import os,fcntl,struct,select,time,json,pathlib
fmt='@llHHi';size=struct.calcsize(fmt);fds={};print(json.dumps({'format':fmt,'size':size,'pointer_bits':struct.calcsize('P')*8}),flush=True)
for p in pathlib.Path('/sys/class/input').glob('event*/device/name'):
 name=p.read_text().strip()
 if name=='LGE RCU' or name.startswith('LGE M-RCU'):
  path='/dev/input/'+p.parts[-3];fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK)
  buf=bytearray(256);fcntl.ioctl(fd,0x81004506,buf,True)
  verified=bytes(buf).split(b'\0')[0].decode(errors='replace');fds[fd]=(path,verified)
  print(json.dumps({'device':path,'name':verified}),flush=True)
end=time.monotonic()+240;last=None
try:
 while time.monotonic()<end and (last is None or time.monotonic()-last<12):
  ready,_,_=select.select(list(fds),[],[],.3)
  for fd in ready:
   data=os.read(fd,size*64)
   if len(data)%size:raise RuntimeError('unaligned input events')
   for i in range(0,len(data),size):
    sec,usec,typ,code,value=struct.unpack(fmt,data[i:i+size])
    if typ==1:
     last=time.monotonic();print(json.dumps({'device':fds[fd][0],'name':fds[fd][1],'type':typ,'code':code,'value':value,'timestamp_valid':abs(sec-time.time())<10 and 0<=usec<1000000,'event_time':sec+usec/1e6}),flush=True)
finally:
 for fd in fds:os.close(fd)
