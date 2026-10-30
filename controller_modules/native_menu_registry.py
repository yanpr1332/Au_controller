"""Read-only Audition Win32 menu registry; enumerates actual native menu command IDs."""
from __future__ import annotations
import ctypes as ct
from ctypes import wintypes as w
from pathlib import Path

class AuditionNativeMenuRegistry:
    def native_menu_catalog(self):
        """Read all currently registered menu labels/IDs, no UI interaction."""
        pid=self._audition_pid()
        u=ct.windll.user32
        u.GetMenu.argtypes=[w.HWND];u.GetMenu.restype=w.HMENU
        u.GetMenuItemCount.argtypes=[w.HMENU];u.GetMenuItemCount.restype=ct.c_int
        u.GetSubMenu.argtypes=[w.HMENU,ct.c_int];u.GetSubMenu.restype=w.HMENU
        u.GetMenuStringW.argtypes=[w.HMENU,w.UINT,w.LPWSTR,ct.c_int,w.UINT]
        u.GetMenuStringW.restype=ct.c_int
        u.GetMenuItemID.argtypes=[w.HMENU,ct.c_int];u.GetMenuItemID.restype=w.UINT
        u.GetMenuState.argtypes=[w.HMENU,w.UINT,w.UINT];u.GetMenuState.restype=w.UINT
        windows=[]
        @ct.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
        def collect(hwnd,ignore):
            p=w.DWORD()
            u.GetWindowThreadProcessId(hwnd,ct.byref(p))
            if p.value!=pid or not u.IsWindowVisible(hwnd):return True
            n=u.GetWindowTextLengthW(hwnd)
            buf=ct.create_unicode_buffer(n+1)
            u.GetWindowTextW(hwnd,buf,n+1)
            if 'Audition' in buf.value and u.GetMenu(hwnd):windows.append(int(hwnd))
            return True
        u.EnumWindows(collect,0)
        if not windows:raise RuntimeError('Audition main window not found')
        hwnd=windows[0]
        root=u.GetMenu(hwnd)
        result=[]
        def walk(menu,prefix,depth):
            if depth>8:return
            count=u.GetMenuItemCount(menu)
            if count<0 or count>512:raise ValueError('Invalid menu size')
            for index in range(count):
                label=ct.create_unicode_buffer(512)
                u.GetMenuStringW(menu,index,label,512,0x400)
                text=label.value.replace('&','').strip()
                submenu=u.GetSubMenu(menu,index)
                cmd=int(u.GetMenuItemID(menu,index))
                flags=int(u.GetMenuState(menu,index,0x400))
                if not text:continue
                path=prefix+[text]
                if cmd not in (0,0xffffffff):
                    result.append({'id':cmd,'name':text,'path':' > '.join(path),
                                   'category':prefix[0] if prefix else text,
                                   'depth':depth,
                                   'menu_enabled':bool(not flags&0x3)})
                if submenu:walk(submenu,path,depth+1)
        walk(root,[],0)
        duplicate={}
        for rec in result:duplicate[rec['id']]=duplicate.get(rec['id'],0)+1
        return {'host':'Audition','pid':pid,'main_window':hwnd,
                'count':len(result),'unique_ids':len(duplicate),
                'duplicated_id_occurrences':sum(v-1 for v in duplicate.values()),
                'commands':result,'discovery':'Win32 GetMenu read-only'}

    def lookup_native_menu(self,keyword:str,*,max_results:int=50):
        if not isinstance(keyword,str) or not 1<=len(keyword)<=100:
            raise ValueError('Search keyword must be 1..100 chars')
        if type(max_results)!=int or not 1<=max_results<=250:
            raise ValueError('Result cap out of bounds')
        catalog=self.native_menu_catalog()
        matches=[x for x in catalog['commands'] if keyword.casefold() in x['path'].casefold()]
        return {'query':keyword,'total_matches':len(matches),'matches':matches[:max_results]}
