#!/usr/bin/env python3
"""Install/restore only com.bnhr.customhome using an existing administrator SSH alias."""
import argparse, hashlib, json, pathlib, shlex, subprocess, tarfile
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('package', type=pathlib.Path)
p.add_argument('--verify-only',action='store_true',help='Validate the recovery package without connecting')
p.add_argument('--log-file',type=pathlib.Path,help='Optional private install-service response log; keep outside Git')
p.add_argument('--ssh-config',required=True,type=pathlib.Path)
p.add_argument('--host',required=True,help='Existing key-only administrator SSH alias')
a=p.parse_args()
data=a.package.read_bytes()
# Validate IPK control/data members before uploading; refuse a different application.
def ar_members(raw):
    assert raw[:8]==b'!<arch>\n', 'Not an IPK archive'
    pos=8
    while pos<len(raw):
        head=raw[pos:pos+60]; size=int(head[48:58]); name=head[:16].decode().strip().rstrip('/')
        yield name,raw[pos+60:pos+60+size]
        pos+=60+size+(size%2)
import io
appinfo=None
for name,body in ar_members(data):
    if name.startswith('data.tar'):
        with tarfile.open(fileobj=io.BytesIO(body),mode='r:*') as archive:
            manifests=[m for m in archive.getmembers() if m.name.endswith('/appinfo.json')]
            assert len(manifests)==1,'Package must contain one application'
            appinfo=json.load(archive.extractfile(manifests[0]))
assert appinfo and appinfo['id']=='com.bnhr.customhome','Unexpected application ID'
if a.verify_only:
    print('Validated '+appinfo['id']+' version '+appinfo['version']+' SHA256 '+hashlib.sha256(data).hexdigest())
    raise SystemExit(0)
ssh=['ssh','-F',str(a.ssh_config),'-T','-o','BatchMode=yes',a.host]
remote='/tmp/bnhr-customhome-update.ipk'
subprocess.run(ssh+['cat > '+remote],input=data,check=True)
sha=hashlib.sha256(data).hexdigest()
r=subprocess.run(ssh+['sha256sum '+remote],capture_output=True,text=True,check=True)
assert r.stdout.split()[0]==sha,'Transfer checksum mismatch'
def luna(method,body,subscribe=False):
    cmd='/usr/bin/luna-send '+('-w 30000 -i ' if subscribe else '-n 1 ')+'luna://com.webos.'+method+' '+shlex.quote(json.dumps(body))
    # Keep stdin open while Luna runs: immediate EOF can suppress responses on webOS.
    proc=subprocess.Popen(ssh+[cmd],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    # Do not communicate(): it closes stdin before the service responds.
    import threading
    chunks=[]
    reader=threading.Thread(target=lambda:chunks.append(proc.stdout.read()),daemon=True);reader.start()
    try:proc.wait(timeout=40)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
    proc.stdin.close();reader.join(timeout=2)
    out=''.join(chunks);err=proc.stderr.read()
    return out
print('Closing only com.bnhr.customhome, then installing version '+appinfo['version'],flush=True)
luna('applicationManager/closeByAppId',{'id':'com.bnhr.customhome'})
result=luna('appInstallService/dev/install',{'id':'com.bnhr.customhome','ipkUrl':remote,'subscribe':True},True)
if a.log_file:
    a.log_file.write_text(result)
responses=[]
for line in result.splitlines():
    try:responses.append(json.loads(line))
    except json.JSONDecodeError:pass
assert any(x.get('id')=='com.bnhr.customhome' and x.get('details',{}).get('state')=='installed' for x in responses),'Installation not confirmed; inspect service output privately before retrying'
print('Installation confirmed: '+appinfo['version'])
print(luna('applicationManager/launch',{'id':'com.bnhr.customhome'}).strip())
subprocess.run(ssh+['rm -f '+remote],check=True)
