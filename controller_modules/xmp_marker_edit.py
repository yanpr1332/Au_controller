"""Guarded native SESX XMP Cue marker editing: add, rename, shift, remove QA markers.

Writes only new ACCEPT_AU_ SESX copies under tests. Application reopen required
before reporting this as a native Audition accepted document.
"""
from __future__ import annotations
import copy,hashlib,re,uuid
from pathlib import Path
from lxml import etree as ET

class AuditionXmpEditor:
    @classmethod
    def patch_native_xmp_markers(cls,source,destination,operations,*,confirm=False):
        from audition_controller import ROOT
        safe=(ROOT/'tests').resolve()
        src,tree,root,tracks=cls._native_tree(source)
        dst=Path(destination).resolve()
        if safe not in src.parents or not src.name.startswith('ACCEPT_AU_'):
            raise PermissionError('Only owned ACCEPT_AU_ SESX sources supported')
        if (dst==src or dst.exists() or safe not in dst.parents or
            not dst.name.startswith('ACCEPT_AU_') or dst.suffix.lower()!='.sesx' or
            not dst.parent.is_dir()):
            raise ValueError('A new QA SESX destination is required')
        if not isinstance(operations,list) or not 1<=len(operations)<=20:
            raise ValueError('1..20 XMP marker operations required')
        packet=root.find('./session/xmpMetadata')
        if packet is None or not packet.text:raise ValueError('XMP packet missing')
        original_text=packet.text
        match=re.search(r'<x:xmpmeta\b[\s\S]*?</x:xmpmeta>',original_text)
        if not match:raise ValueError('Native XMP metadata unavailable')
        xmp=ET.fromstring(match.group(0).encode('utf8'))
        nspace='http://ns.adobe.com/xmp/1.0/DynamicMedia/'
        rdfspace='http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        prefix={'xmpDM':nspace,'rdf':rdfspace}
        seq=xmp.find('.//xmpDM:Tracks/rdf:Bag/rdf:li/xmpDM:markers/rdf:Seq',namespaces=prefix)
        if seq is None:raise ValueError('No XMP Cue marker sequence')
        count=len(seq)
        def get(el,key):
            obj=el.find('{'+nspace+'}'+key)
            return obj.text if obj is not None else None
        def setvalue(el,key,value):
            node=el.find('{'+nspace+'}'+key)
            if node is None:
                raise ValueError('Unsupported marker schema: '+key)
            node.text=str(value)
        def qa_name(name):
            if (not isinstance(name,str) or not name.startswith('QA ') or len(name)>75 or
                any(ord(ch)<32 for ch in name)):
                raise ValueError('QA marker names must start QA and be <=75 chars')
            return name
        def get_by_name(name):
            matchers=[el for el in seq if get(el,'name')==name]
            if len(matchers)!=1:raise ValueError('Marker must exist exactly once: '+name)
            return matchers[0]
        used=set(get(el,'name') for el in seq)
        for op in operations:
            if not isinstance(op,dict) or op.get('action') not in ('add','remove','move','rename'):
                raise ValueError('Unknown native XMP marker action')
            action=op['action']
            name=qa_name(op.get('name'))
            if action=='add':
                if name in used:raise ValueError('Duplicate marker name')
                sample=op.get('start_samples');duration=op.get('duration_samples')
                if type(sample)!=int or type(duration)!=int or not 0<=sample<=48_000_000 or not 0<=duration<=48_000_000:
                    raise ValueError('Invalid marker start/duration')
                if count==0 and not len(seq):raise ValueError('A native marker template is required')
                template=copy.deepcopy(seq[0])
                setvalue(template,'name',name)
                setvalue(template,'startTime',sample)
                setvalue(template,'duration',duration)
                setvalue(template,'comment',str(op.get('comment','QA Audition Marker'))[:150])
                guid='xmp:id:'+str(uuid.uuid4())
                setvalue(template,'guid',guid)
                for item in template.xpath('.//xmpDM:key[text()="marker_guid"]/../xmpDM:value',namespaces=prefix):
                    item.text=guid
                seq.append(template)
                used.add(name)
            elif action=='remove':
                obj=get_by_name(name);seq.remove(obj);used.discard(name)
            elif action=='move':
                obj=get_by_name(name)
                sample=op.get('start_samples')
                duration=op.get('duration_samples')
                if type(sample)!=int or not 0<=sample<=48_000_000:
                    raise ValueError('Invalid marker new start')
                setvalue(obj,'startTime',sample)
                if duration is not None:
                    if type(duration)!=int or not 0<=duration<=48_000_000:
                        raise ValueError('Invalid duration')
                    setvalue(obj,'duration',duration)
            elif action=='rename':
                new=qa_name(op.get('new_name'))
                if new in used:raise ValueError('New name conflicts with existing marker')
                obj=get_by_name(name)
                setvalue(obj,'name',new)
                used.remove(name);used.add(new)
        if not confirm:return {'dry_run':True,'old_markers':count,
                               'new_markers':len(seq),'output':str(dst)}
        old_hash=hashlib.sha256(src.read_bytes()).hexdigest()
        new_text=ET.tostring(xmp,encoding='unicode')
        packet.text=original_text[:match.start()]+new_text+original_text[match.end():]
        serial=ET.tostring(root,encoding='utf8',xml_declaration=True)
        serial=serial.replace(b'\xef\xbb\xbf',b'&#xFEFF;')
        ET.fromstring(serial)
        dst.write_bytes(serial)
        try:
            check=cls.native_sesx_markers_xmp(dst)
            if check['count']!=len(seq):raise ValueError('XMP count not preserved')
            if hashlib.sha256(src.read_bytes()).hexdigest()!=old_hash:
                raise RuntimeError('Source file changed')
        except Exception:
            dst.unlink(missing_ok=True)
            raise
        return {'output':str(dst),'before_count':count,'after_count':len(seq),
                'operations':len(operations),'markers':check['markers'],
                'native_reopen_verified':False,'source_unchanged':True,
                'source_sha256':old_hash,'output_sha256':hashlib.sha256(serial).hexdigest()}
