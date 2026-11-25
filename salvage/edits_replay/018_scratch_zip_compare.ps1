cd G:\GameDev\speculative-markets; py -3 -c @"
import zipfile
a={i.filename:i.file_size for i in zipfile.ZipFile('beta/release_130/releases/Speculative_Markets_Beta_1.3.0-beta.1.zip').infolist()}
b={i.filename:i.file_size for i in zipfile.ZipFile('beta/candidate_131/releases/Speculative_Markets_Beta_1.3.1-beta.1.zip').infolist()}
print(len(a),len(b))
for k in sorted(set(a)|set(b)):
    if k not in a or k not in b or abs(a[k]-b[k])>3000: print(k,a.get(k),b.get(k))
"@
(Select-String beta\candidate_131\mod\common\script_values\spec_values.txt -Pattern 'spec_credit_payoff').Count
