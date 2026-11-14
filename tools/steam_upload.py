"""Scoped Steam Workshop uploader; defaults to a read-only plan.

Only the registered, fingerprinted workshop/upload_staging/ folders are accepted.
Uses the installed game's Valve steam_api64.dll and the current Steam session.
No credentials, launcher DB changes, or legal-agreement acceptance are involved.
Mutating commands require --execute and a separately reviewed invocation.

ABI: Windows pack(8), callback base3400, structures and flat signatures verified
against ValveSoftware/source-sdk-2013/src/public/steam/{isteamugc.h,
steamclientpublic.h,steam_api_internal.h,steam_api_flat.h,isteamremotestorage.h}.
https://partner.steamgames.com/doc/api/ISteamUGC
https://partner.steamgames.com/doc/api/ISteamUtils
"""
import argparse
import ctypes as C
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "workshop/upload_staging"
RECEIPTS = ROOT / "workshop/upload_receipts"
DLL = Path("G:/SteamLibrary/steamapps/common/Victoria 3/binaries/steam_api64.dll")
APP = 529340
STABLE = 3831434383
CMF_PARENT = 3385002128
INVALID = 2**64 - 1
CHANNELS = {
    "stable": ("speculative_markets", "Speculative Markets", "workshop/description.bbcode"),
    "beta": ("speculative_markets_beta", "Speculative Markets - Beta", "beta/workshop_description.bbcode"),
    "cmf": ("speculative_markets_cmf_compat", "Speculative Markets - CMF Compatibility", "compatibility/cmf/workshop_description.bbcode"),
    "morgenroete": ("speculative_markets_morgenroete", "Speculative Markets - Morgenroete Compatibility", "compatibility/morgenroete/workshop_description.bbcode"),
}
U64, U32, I32, PTR = C.c_uint64, C.c_uint32, C.c_int32, C.c_void_p


class QueryResult(C.Structure):
    _pack_ = 8
    _fields_ = [("handle", U64), ("result", I32), ("returned", U32),
                ("total", U32), ("cached", C.c_bool), ("next_cursor", C.c_char * 256)]


class CreateResult(C.Structure):
    _pack_ = 8
    _fields_ = [("result", I32), ("item", U64), ("legal_required", C.c_bool)]


class SubmitResult(C.Structure):
    _pack_ = 8
    _fields_ = [("result", I32), ("legal_required", C.c_bool), ("item", U64)]


class StringArray(C.Structure):
    _pack_ = 8
    _fields_ = [("strings", C.POINTER(C.c_char_p)), ("count", I32)]


class Details(C.Structure):
    _pack_ = 8
    _fields_ = [("item", U64), ("result", I32), ("file_type", I32),
                ("creator_app", U32), ("consumer_app", U32),
                ("title", C.c_char * 129), ("description", C.c_char * 8000),
                ("owner", U64), ("created", U32), ("updated", U32),
                ("added", U32), ("visibility", I32), ("banned", C.c_bool),
                ("accepted", C.c_bool), ("tags_truncated", C.c_bool),
                ("tags", C.c_char * 1025), ("file", U64), ("preview", U64),
                ("filename", C.c_char * 260), ("file_size", I32),
                ("preview_size", I32), ("url", C.c_char * 256),
                ("votes_up", U32), ("votes_down", U32), ("score", C.c_float), ("children", U32)]


assert (C.sizeof(QueryResult), C.sizeof(CreateResult), C.sizeof(SubmitResult)) == (280, 24, 16)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def immutable(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def receipt(action, channel, data):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = RECEIPTS / f"{stamp}_{channel}_{action}_{uuid.uuid4().hex[:8]}.json"
    immutable(path, {"utc": stamp, "action": action, "channel": channel, **data})
    emit({"receipt": str(path), "action": action})


def inspect_stage(channel):
    item = json.loads((STAGING / "manifest.json").read_text(encoding="utf-8"))["items"][channel]
    folder = STAGING / channel
    if folder.resolve() != folder:
        raise ValueError("Staging directory is redirected")
    hashes = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError(f"Redirected staged file: {path}")
        if path.is_file():
            hashes[path.relative_to(folder).as_posix()] = sha(path.read_bytes())
    if hashes != item["files_sha256"]:
        raise ValueError("Staged files no longer match their accepted upload manifest")
    metadata = json.loads((folder / ".metadata/metadata.json").read_text(encoding="utf-8"))
    if metadata["id"] != CHANNELS[channel][0] or metadata["version"] != item["version"]:
        raise ValueError("Staged mod identity/version mismatch")
    if any(rel.get("rel_type") != "dependency" for rel in metadata.get("relationships", [])):
        raise ValueError("Game-rejected metadata relationship")
    thumbnail = folder / "thumbnail.png"
    if not (16 <= thumbnail.stat().st_size < 1048576):
        raise ValueError("Preview must be between16bytes and1MiB")
    return {"channel": channel, "folder": str(folder), "id": metadata["id"],
            "version": metadata["version"], "title": CHANNELS[channel][1],
            "tags": metadata.get("tags", []), "file_count": len(hashes),
            "files_sha256": hashes, "source_archive_sha256": item["source_archive_sha256"]}


def description(channel):
    path = ROOT / CHANNELS[channel][2]
    text = path.read_text(encoding="utf-8").strip()
    if re.search(r"__[A-Z][A-Z0-9_]*__", text):
        raise ValueError(f"Unresolved publication placeholder in {path}")
    raw = text.encode("utf-8")
    if not raw or len(raw) >= 8000 or b"\0" in raw:
        raise ValueError("Description must be nonempty UTF-8 under8000bytes without NUL")
    return text, sha(raw)


def changelog(plan):
    folder = {"stable": "workshop", "beta": "beta", "cmf": "compatibility/cmf", "morgenroete": "compatibility/morgenroete"}[plan['channel']]
    path = ROOT / folder / f"changelog_{plan['version']}.bbcode"
    text = path.read_text(encoding="utf-8").strip()
    if not text or "\0" in text or len(text.encode("utf-8")) >= 8000:
        raise ValueError(f"Invalid changelog: {path}")
    return text


def known_id(channel):
    if channel == "stable":
        return STABLE
    path = RECEIPTS / f"{channel}.binding.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    item = int(data["item_id"])
    if data["channel"] != channel or data["app_id"] != APP or item in (STABLE, CMF_PARENT) or item <= 0:
        raise ValueError("Invalid channel binding")
    return item


class Steam:
    def __init__(self):
        if sys.platform != "win32" or C.sizeof(PTR) != 8:
            raise RuntimeError("This ABI is Windows64 only")
        os.environ["SteamAppId"] = str(APP)
        os.environ["SteamGameId"] = str(APP)
        self.dll_dir = os.add_dll_directory(str(DLL.parent))
        self.api = C.CDLL(str(DLL))
        self.bind("SteamAPI_Init", C.c_bool, [])
        self.bind("SteamAPI_Shutdown", None, [])
        self.bind("SteamAPI_RunCallbacks", None, [])
        for name in ("SteamUGC_v016", "SteamUtils_v010", "SteamUser_v021"):
            self.bind("SteamAPI_" + name, PTR, [])
        if not self.api.SteamAPI_Init():
            raise RuntimeError("SteamAPI_Init failed; no authentication bypass attempted")
        self.ugc = self.api.SteamAPI_SteamUGC_v016()
        self.utils = self.api.SteamAPI_SteamUtils_v010()
        self.user = self.api.SteamAPI_SteamUser_v021()
        if not all((self.ugc, self.utils, self.user)):
            self.close()
            raise RuntimeError("Required Steam interface unavailable")
        self.bind("SteamAPI_ISteamUtils_GetAppID", U32, [PTR])
        self.bind("SteamAPI_ISteamUser_BLoggedOn", C.c_bool, [PTR])
        self.bind("SteamAPI_ISteamUser_GetSteamID", U64, [PTR])
        if self.api.SteamAPI_ISteamUtils_GetAppID(self.utils) != APP or not self.api.SteamAPI_ISteamUser_BLoggedOn(self.user):
            self.close()
            raise RuntimeError("Wrong AppID or unauthenticated Steam session")
        self.owner = self.api.SteamAPI_ISteamUser_GetSteamID(self.user)
        self.bind("SteamAPI_ISteamUtils_IsAPICallCompleted", C.c_bool, [PTR, U64, C.POINTER(C.c_bool)])
        self.bind("SteamAPI_ISteamUtils_GetAPICallResult", C.c_bool, [PTR, U64, PTR, I32, I32, C.POINTER(C.c_bool)])
        self.ugcb("CreateQueryUGCDetailsRequest", U64, [C.POINTER(U64), U32])
        self.ugcb("SetAllowCachedResponse", C.c_bool, [U64, U32])
        self.ugcb("SetReturnLongDescription", C.c_bool, [U64, C.c_bool])
        self.ugcb("SetReturnChildren", C.c_bool, [U64, C.c_bool])
        self.ugcb("SetLanguage", C.c_bool, [U64, C.c_char_p])
        self.ugcb("SendQueryUGCRequest", U64, [U64])
        self.ugcb("GetQueryUGCResult", C.c_bool, [U64, U32, C.POINTER(Details)])
        self.ugcb("GetQueryUGCChildren", C.c_bool, [U64, U32, C.POINTER(U64), U32])
        self.ugcb("ReleaseQueryUGCRequest", C.c_bool, [U64])
        self.ugcb("CreateItem", U64, [U32, I32])
        self.ugcb("StartItemUpdate", U64, [U32, U64])
        for name in ("SetItemContent", "SetItemPreview", "SetItemTitle", "SetItemDescription", "SetItemUpdateLanguage"):
            self.ugcb(name, C.c_bool, [U64, C.c_char_p])
        self.ugcb("SetItemVisibility", C.c_bool, [U64, I32])
        self.ugcb("SetItemTags", C.c_bool, [U64, C.POINTER(StringArray)])
        self.ugcb("SubmitItemUpdate", U64, [U64, C.c_char_p])
        self.ugcb("GetItemUpdateProgress", I32, [U64, C.POINTER(U64), C.POINTER(U64)])

    def bind(self, name, returns, args):
        fn = getattr(self.api, name)
        fn.restype, fn.argtypes = returns, args
        return fn

    def ugcb(self, name, returns, args):
        self.bind("SteamAPI_ISteamUGC_" + name, returns, [PTR, *args])

    def ugc_call(self, name, *args):
        return getattr(self.api, "SteamAPI_ISteamUGC_" + name)(self.ugc, *args)

    def close(self):
        self.api.SteamAPI_Shutdown()
        self.dll_dir.close()

    def wait(self, call, typ, callback, timeout=120, update=None):
        if not call:
            raise RuntimeError("Steam returned an invalid async call handle")
        start, last = time.monotonic(), 0
        while time.monotonic() - start < timeout:
            self.api.SteamAPI_RunCallbacks()
            failed = C.c_bool()
            if self.api.SteamAPI_ISteamUtils_IsAPICallCompleted(self.utils, call, C.byref(failed)):
                result = typ()
                ok = self.api.SteamAPI_ISteamUtils_GetAPICallResult(
                    self.utils, call, C.byref(result), C.sizeof(result), callback, C.byref(failed))
                if not ok or failed.value:
                    raise RuntimeError("Steam async result unavailable or I/O failed; do not blindly retry a mutation")
                return result
            if update is not None and time.monotonic() - last >= 10:
                done, total = U64(), U64()
                phase = self.ugc_call("GetItemUpdateProgress", update, C.byref(done), C.byref(total))
                emit({"upload_phase": phase, "processed": done.value, "total": total.value})
                last = time.monotonic()
            time.sleep(0.1)
        raise TimeoutError("Steam result timed out; operation may have completed remotely. Do not blindly retry")

    def query(self, item):
        ids = (U64 * 1)(item)
        handle = self.ugc_call("CreateQueryUGCDetailsRequest", ids, 1)
        if handle in (0, INVALID):
            raise RuntimeError("Invalid UGC query handle")
        try:
            for name, value in (("SetAllowCachedResponse", 0), ("SetReturnLongDescription", True),
                                ("SetReturnChildren", True), ("SetLanguage", b"english")):
                if not self.ugc_call(name, handle, value):
                    raise RuntimeError(f"{name} failed")
            result = self.wait(self.ugc_call("SendQueryUGCRequest", handle), QueryResult, 3401)
            if result.result != 1 or result.handle != handle or result.returned != 1:
                raise RuntimeError(f"UGC query failed: EResult={result.result}, returned={result.returned}")
            details = Details()
            if not self.ugc_call("GetQueryUGCResult", handle, 0, C.byref(details)):
                raise RuntimeError("GetQueryUGCResult failed")
            if details.item != item or details.result != 1 or details.consumer_app != APP or details.owner != self.owner or details.banned:
                raise RuntimeError("Item ID/result/application/owner/banned-state verification failed")
            if details.children > 10000:
                raise RuntimeError("Unexpected child count; refuse oversized result")
            children = (U64 * details.children)()
            if details.children and not self.ugc_call("GetQueryUGCChildren", handle, 0, children, details.children):
                raise RuntimeError("Failed to retrieve required Workshop item IDs")
            return {"item_id": item, "consumer_app": details.consumer_app, "creator_app": details.creator_app,
                    "owned_by_current_user": True, "title": details.title.decode("utf-8"),
                    "visibility": details.visibility, "file_size": details.file_size,
                    "preview_size": details.preview_size, "updated": details.updated,
                    "description_sha256": sha(bytes(details.description)),
                    "tags": details.tags.decode("utf-8"), "children": details.children, "child_ids": list(children)}
        finally:
            self.ugc_call("ReleaseQueryUGCRequest", handle)

    def submit(self, item, plan, text, visibility, content=True):
        handle = self.ugc_call("StartItemUpdate", APP, item)
        if handle in (0, INVALID):
            raise RuntimeError("Invalid UGC update handle")
        values = [("SetItemUpdateLanguage", b"english"), ("SetItemTitle", plan["title"].encode("utf-8")),
                  ("SetItemDescription", text.encode("utf-8")), ("SetItemVisibility", visibility)]
        if content:
            values += [("SetItemContent", plan["folder"].encode("utf-8")),
                       ("SetItemPreview", str(Path(plan["folder"]) / "thumbnail.png").encode("utf-8"))]
        for name, value in values:
            if not self.ugc_call(name, handle, value):
                raise RuntimeError(f"Steam rejected {name}; nothing submitted")
        raw_tags = [tag.encode("utf-8") for tag in plan["tags"]]
        strings = (C.c_char_p * len(raw_tags))(*raw_tags)
        tags = StringArray(strings, len(raw_tags))
        if not self.ugc_call("SetItemTags", handle, C.byref(tags)):
            raise RuntimeError("Steam rejected tags; nothing submitted")
        change_note = f"Speculative Markets {plan['version']}"
        if content:
            change_note = plan["changelog"]
        call = self.ugc_call("SubmitItemUpdate", handle, change_note.encode("utf-8"))
        result = self.wait(call, SubmitResult, 3404, timeout=1200, update=handle)
        if result.item != item or result.result != 1:
            raise RuntimeError(f"Submit failed: EResult={result.result}, item={result.item}, legal_required={result.legal_required}")
        if result.legal_required:
            raise RuntimeError(f"Workshop legal agreement requires user action for item{item}; no acceptance attempted")
        return {"item_id": item, "result": result.result, "legal_required": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("plan", "query", "create", "update"), default="plan")
    parser.add_argument("channel", nargs="?", choices=CHANNELS, default="stable")
    parser.add_argument("--execute", action="store_true", help="Explicitly perform a reviewed create/update")
    parser.add_argument("--public", action="store_true", help="Publish update publicly; otherwise keep private")
    parser.add_argument("--description-only", action="store_true", help="Update listing metadata without replacing content or preview")
    parser.add_argument("--gate", type=Path, help="Complete automated release-gate report for stable/beta content updates")
    args = parser.parse_args(argv)
    if args.description_only and args.command != "update":
        parser.error("--description-only requires update")
    steam = None
    try:
        plan = inspect_stage(args.channel)
        if args.command in ("plan", "update"):
            plan["changelog"] = changelog(plan)
        item = known_id(args.channel)
        summary = {k: v for k, v in plan.items() if k != "files_sha256"}
        summary.update(command=args.command, item_id=item, execute=args.execute, visibility=0 if args.public else 2)
        summary["description_only"] = args.description_only
        if args.command in ("plan", "update"):
            body, body_hash = description(args.channel)
            summary["description_sha256"] = body_hash
        emit(summary)
        if args.command == "plan" or args.command in ("create", "update") and not args.execute:
            emit({"dry_run": True, "message": "No Steam mutation performed"})
            return
        if args.command == "update" and args.channel in ("stable", "beta") and not args.description_only:
            if args.gate is None:
                raise ValueError("Stable/beta content uploads require --gate with a complete passing automated report; live UI requirements still apply")
            import release_gate
            accepted_gate = release_gate.verify_report(args.gate.resolve(), Path(plan['folder']))
            emit({"automated_release_gate": str(args.gate.resolve()), "automatic_pass": True,
                  "manual_and_excluded": accepted_gate['manual_and_excluded']})
        if args.command == "create" and (args.channel == "stable" or item is not None or args.public):
            raise ValueError("Create is only for unbound separate items and must remain private")
        if args.command == "update" and args.channel == "stable" and not args.public:
            raise ValueError("Stable updates require --public; refuse accidental unpublication")
        if args.command in ("query", "update") and item is None:
            raise ValueError("No known item binding; create privately first")
        steam = Steam()
        # Every operation authenticates ownership of the fixed existing main mod.
        stable = steam.query(STABLE)
        emit({"stable_owner_check": stable})
        if args.command == "query":
            result = stable if item == STABLE else steam.query(item)
            emit({"query": result})
            receipt("query", args.channel, result)
            return
        if args.command == "create":
            # Permanent intent prevents duplicate creations after ambiguous errors.
            immutable(RECEIPTS / f"{args.channel}.create_intent.json", {"channel": args.channel, "app_id": APP, "plan": plan,
                "utc": datetime.now(timezone.utc).isoformat(), "warning": "Do not retry creation without reconciling this intent"})
            receipt("create_intent", args.channel, {"plan": plan})
            result = steam.wait(steam.ugc_call("CreateItem", APP, 0), CreateResult, 3403)
            recorded = {"channel": args.channel, "app_id": APP, "item_id": result.item,
                        "result": result.result, "legal_required": bool(result.legal_required)}
            receipt("create_result", args.channel, recorded)
            if result.result != 1 or result.item in (0, INVALID, STABLE, CMF_PARENT):
                raise RuntimeError(f"Create result rejected: {recorded}")
            immutable(RECEIPTS / f"{args.channel}.binding.json", recorded)
            if result.legal_required:
                raise RuntimeError(f"Workshop legal agreement requires user action for item{result.item}; no acceptance attempted")
            receipt("private_prepare_intent", args.channel, {"item_id": result.item, "plan": plan})
            prepared = steam.submit(result.item, plan, "Private preparation of " + plan["title"] + ".", 2, content=False)
            receipt("private_prepared", args.channel, prepared)
            observed = steam.query(result.item)
            if observed["visibility"] != 2 or observed["title"] != plan["title"]:
                receipt("private_prepare_mismatch", args.channel, observed)
                raise RuntimeError("New item's private visibility/title did not verify")
            receipt("private_verified", args.channel, observed)
            emit({"created_private": observed})
            return
        before = stable if item == STABLE else steam.query(item)
        # Re-read hashes immediately before submitting content; receipts preserve
        # the exact description and source inventory used for this transaction.
        refreshed = inspect_stage(args.channel)
        refreshed["changelog"] = changelog(refreshed)
        if refreshed != plan:
            raise ValueError("Staging changed during preflight")
        submit_plan = dict(plan)
        if args.channel == "stable":
            # Preserve the current published spelling of existing tags.
            submit_plan["tags"] = [tag for tag in before["tags"].split(",") if tag]
        receipt("update_intent", args.channel, {"item_id": item, "before": before, "plan": submit_plan,
                "description": body, "description_sha256": body_hash, "visibility": 0 if args.public else 2,
                "description_only": args.description_only})
        result = steam.submit(item, submit_plan, body, 0 if args.public else 2, content=not args.description_only)
        receipt("update_result", args.channel, result)
        after = steam.query(item)
        if after["title"] != plan["title"] or after["description_sha256"] != body_hash or after["visibility"] != (0 if args.public else 2):
            receipt("update_observed_mismatch", args.channel, after)
            raise RuntimeError("Post-upload title/description/visibility do not match; inspect receipt before retry")
        receipt("update_verified", args.channel, after)
        emit({"published": after, "url": f"https://steamcommunity.com/sharedfiles/filedetails/?id={item}"})
    except (OSError, ValueError, RuntimeError, TimeoutError, KeyError) as error:
        if args.execute:
            receipt("error", args.channel, {"command": args.command, "error": str(error), "retry_automatically": False})
        parser.exit(1, f"Steam upload stopped: {error}\n")
    finally:
        if steam is not None:
            steam.close()


if __name__ == "__main__":
    main()
