"""Read actual PE icon resources, not merely an ICO embedded in a ZIP payload."""
import struct

def icon_images(data):
 pe=struct.unpack_from('<I',data,0x3c)[0]
 if data[:2]!=b'MZ' or data[pe:pe+4]!=b'PE\0\0':raise ValueError('Not a PE file')
 count=struct.unpack_from('<H',data,pe+6)[0];size=struct.unpack_from('<H',data,pe+20)[0]
 optional=pe+24;plus=struct.unpack_from('<H',data,optional)[0]==0x20b
 directories=optional+(112 if plus else 96)
 resource_rva,resource_size=struct.unpack_from('<II',data,directories+16)
 if not resource_rva or not resource_size:raise ValueError('No PE resources')
 sections=optional+size
 def offset(rva):
  for i in range(count):
   entry=sections+i*40;virtual_size,address,raw_size,pointer=struct.unpack_from('<IIII',data,entry+8)
   if address<=rva<address+max(virtual_size,raw_size):return pointer+rva-address
  raise ValueError('Resource address outside PE sections')
 base=offset(resource_rva);resources={}
 def walk(relative,path=()):
  if len(path)>3:raise ValueError('Invalid resource depth')
  directory=base+relative;named,ids=struct.unpack_from('<HH',data,directory+12)
  for i in range(named+ids):
   name,target=struct.unpack_from('<II',data,directory+16+i*8)
   if name&0x80000000:continue
   key=path+(name,)
   if target&0x80000000:walk(target&0x7fffffff,key)
   else:
    rva,length=struct.unpack_from('<II',data,base+target);begin=offset(rva)
    resources[key]=data[begin:begin+length]
 walk(0)
 if not any(key[:2]==(14,32512) for key in resources):raise ValueError('Missing application icon group 32512')
 return [value for key,value in resources.items() if key[0]==3]

def verify_icon(data,ico):
 images=icon_images(data);count=struct.unpack_from('<H',ico,4)[0]
 expected=[]
 for i in range(count):
  length,offset=struct.unpack_from('<II',ico,6+i*16+8);expected.append(ico[offset:offset+length])
 if not expected or any(image not in images for image in expected):raise ValueError('PE does not contain the current AniCanto icon images')
 return dict(images=len(images),sourceSizes=len(expected),applicationGroup=32512)
