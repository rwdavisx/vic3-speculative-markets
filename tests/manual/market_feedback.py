"""Stage a player-only decision to inspect a category bulletin and the Finance trust receipt."""
import argparse
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import centres


def prepare(parent, dest):
    shutil.copytree(parent, dest)
    monthly = (dest / "common/scripted_effects/spec_centre_effects.txt").read_text("utf-8-sig")
    review = centres._trust_review("\t\t\t")
    assert review in monthly
    # Exercise the actual money-market loss, including caps. The marker in the packaged goods
    # branch is checked before copying it into the test decision, independent of local tuning.
    scripts = [p.read_text("utf-8-sig") for p in (dest/"common").rglob("*.txt")
               if p.parent.name in ("on_actions","scripted_effects")]
    goods = centres.boom_end("grain", 2, 1 / 3)
    assert any(" ".join(goods.split()) in " ".join(s.split()) for s in scripts)
    assert any(" ".join(centres.PANIC.split()) in " ".join(s.split()) for s in scripts)
    action = """
namespace = spec_feedback_test
spec_feedback_test.1 = {
    type = country_event
    hidden = yes
    immediate = {
        set_variable = { name = spec_exch_known value = 2 }
        set_variable = { name = spec_centre_trust value = 60 }
        remove_variable = spec_issue_grain
        remove_variable = spec_trust_review
        REVIEW
        GOODS
        PANIC_EFFECT
        change_variable = { name = spec_centre_trust add = 1 }
        REVIEW
        set_local_variable = { name = feedback_sum value = { value = var:spec_trust_goods_last add = var:spec_trust_panics_last add = 1 } }
        set_local_variable = { name = feedback_actual value = { value = var:spec_centre_trust subtract = 60 } }
        if = { limit = {
            var:spec_trust_goods_last < 0 var:spec_trust_panics_last < 0
            var:spec_trust_change = local_var:feedback_sum
            var:spec_trust_change = local_var:feedback_actual
        } debug_log = "HOTFIX PASS actual_player_trust_receipt_reconciles" }
        else = { debug_log = "HOTFIX FAIL actual_player_trust_receipt_reconciles" }
        spec_clear_market_news = yes
        spec_queue_market_news = { FIELD = food_hot }
        spec_queue_market_news = { FIELD = food_hot }
        spec_queue_market_news = { FIELD = industry_correction }
        spec_queue_market_news = { FIELD = defence_collapse }
        spec_queue_market_news = { FIELD = opinions }
        set_variable = spec_news_urgent
        spec_deliver_market_news = yes
    }
}
"""
    button = dest / "common/decisions/zz_feedback_test.txt"
    button.parent.mkdir(exist_ok=True)
    button.write_text("""spec_feedback_inspect = {
    is_shown = { is_player = yes has_variable = spec_conf }
    possible = { always = yes }
    ai_chance = { value = 0 }
    when_taken = { trigger_event = { id = spec_feedback_test.1 } }
}
""", encoding="utf-8-sig")
    (dest / "events/zz_feedback_test.txt").write_text(
        action.replace("REVIEW", review).replace("GOODS", goods).replace("PANIC_EFFECT", centres.PANIC),
        encoding="utf-8-sig")
    (dest / "localization/english/zz_feedback_test_l_english.yml").write_text(
        'l_english:\n spec_feedback_inspect: "Inspect Market Bulletin"\n'
        ' spec_feedback_inspect_desc: "Exercise the Money Market trust receipt and post a sample domestic bulletin."\n',
        encoding="utf-8-sig")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.source, args.out)
