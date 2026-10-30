"""WinMM device discovery and bounded MIDI messages for control surfaces.

Raw MIDI transport; host-specific HUI/Mackie state synchronization is separate.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes as w
import math
import time
import winreg


class _MidiInCaps(ctypes.Structure):
    _fields_=[('manufacturer',w.WORD),('product',w.WORD),('driver',w.DWORD),('name',w.WCHAR*32),('support',w.DWORD)]


class _MidiOutCaps(ctypes.Structure):
    _fields_=[('manufacturer',w.WORD),('product',w.WORD),('driver',w.DWORD),('name',w.WCHAR*32),('technology',w.WORD),('voices',w.WORD),('notes',w.WORD),('channel_mask',w.WORD),('support',w.DWORD)]


class AuditionControlSurface:
    @staticmethod
    def _midi_devices(direction):
        mm=ctypes.WinDLL('winmm')
        caps_type=_MidiInCaps if direction=='input' else _MidiOutCaps
        get_count=mm.midiInGetNumDevs if direction=='input' else mm.midiOutGetNumDevs
        get_caps=mm.midiInGetDevCapsW if direction=='input' else mm.midiOutGetDevCapsW
        get_caps.argtypes=[ctypes.c_size_t,ctypes.POINTER(caps_type),w.UINT]
        get_caps.restype=w.UINT
        devices=[]
        for index in range(get_count()):
            caps=caps_type();code=get_caps(index,ctypes.byref(caps),ctypes.sizeof(caps))
            if code:raise OSError(code,'Cannot query MIDI device')
            devices.append(dict(id=index,name=caps.name,manufacturer=caps.manufacturer,product=caps.product))
        return devices

    @classmethod
    def control_surface_devices(cls):
        asio=[]
        for hive,label in ((winreg.HKEY_LOCAL_MACHINE,'machine'),(winreg.HKEY_CURRENT_USER,'user')):
            for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive,r'SOFTWARE\ASIO',0,winreg.KEY_READ|view) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            name=winreg.EnumKey(key,i)
                            if not any(x['name']==name and x['scope']==label for x in asio):asio.append(dict(name=name,scope=label))
                except FileNotFoundError:pass
        return dict(midi_inputs=cls._midi_devices('input'),midi_outputs=cls._midi_devices('output'),asio_drivers=asio,
                    native_audition_device_selection_verified=False)

    @staticmethod
    def midi_control_message(channel,controller,value):
        if any(type(x) is not int for x in (channel,controller,value)) or not 1<=channel<=16 or not 0<=controller<=127 or not 0<=value<=127:
            raise ValueError('MIDI channel 1..16, controller/value 0..127 required')
        status=0xB0+channel-1
        return dict(channel=channel,controller=controller,value=value,bytes=[status,controller,value],packed=status|(controller<<8)|(value<<16))

    @staticmethod
    def decode_midi_message(packed):
        if type(packed) is not int or not 0<=packed<=0xFFFFFF:raise ValueError('Three-byte MIDI message required')
        status=packed&255;data1=(packed>>8)&255;data2=(packed>>16)&255
        if not 0x80<=status<=0xEF or data1>127 or data2>127:raise ValueError('Invalid channel MIDI message')
        kind={0x80:'note_off',0x90:'note_on',0xA0:'poly_pressure',0xB0:'control_change',0xC0:'program_change',0xD0:'channel_pressure',0xE0:'pitch_bend'}[status&0xF0]
        return dict(type=kind,channel=(status&15)+1,data1=data1,data2=data2,pitch_bend=(data1|(data2<<7)) if kind=='pitch_bend' else None)

    @classmethod
    def send_midi_control(cls,device_id,*,channel,controller,value,confirm=False):
        message=cls.midi_control_message(channel,controller,value)
        devices=cls._midi_devices('output')
        if type(device_id) is not int or not 0<=device_id<len(devices) or type(confirm) is not bool:raise ValueError('Existing output device and Boolean confirmation required')
        if not confirm:return dict(dry_run=True,device=devices[device_id],message=message)
        mm=ctypes.WinDLL('winmm');handle=w.HANDLE()
        mm.midiOutOpen.argtypes=[ctypes.POINTER(w.HANDLE),w.UINT,ctypes.c_size_t,ctypes.c_size_t,w.DWORD]
        mm.midiOutShortMsg.argtypes=[w.HANDLE,w.DWORD];mm.midiOutClose.argtypes=[w.HANDLE]
        code=mm.midiOutOpen(ctypes.byref(handle),device_id,0,0,0)
        if code:raise OSError(code,'Unable to open MIDI output')
        try:
            code=mm.midiOutShortMsg(handle,message['packed'])
            if code:raise OSError(code,'MIDI output failed')
        finally:mm.midiOutClose(handle)
        return dict(dry_run=False,device=devices[device_id],message=message,sent=True,audition_feedback_verified=False)

    @classmethod
    def listen_midi_controls(cls,device_id,*,seconds=1.0,confirm=False):
        devices=cls._midi_devices('input')
        if type(device_id) is not int or not 0<=device_id<len(devices) or type(seconds) not in (int,float) or not math.isfinite(seconds) or not .1<=seconds<=5 or type(confirm) is not bool:
            raise ValueError('Existing input, .1..5 seconds and Boolean confirmation required')
        if not confirm:return dict(dry_run=True,device=devices[device_id],seconds=seconds)
        mm=ctypes.WinDLL('winmm');handle=w.HANDLE();events=[]
        callback_type=ctypes.WINFUNCTYPE(None,w.HANDLE,w.UINT,ctypes.c_size_t,ctypes.c_size_t,ctypes.c_size_t)
        @callback_type
        def callback(device,event,instance,data,timestamp):
            if event==0x3C3 and len(events)<4096:
                try:events.append(dict(timestamp_ms=int(timestamp),message=cls.decode_midi_message(int(data)&0xFFFFFF)))
                except ValueError:pass
        mm.midiInOpen.argtypes=[ctypes.POINTER(w.HANDLE),w.UINT,callback_type,ctypes.c_size_t,w.DWORD]
        for name in ('midiInStart','midiInStop','midiInReset','midiInClose'):getattr(mm,name).argtypes=[w.HANDLE]
        code=mm.midiInOpen(ctypes.byref(handle),device_id,callback,0,0x00030000)
        if code:raise OSError(code,'Unable to open MIDI input')
        try:
            code=mm.midiInStart(handle)
            if code:raise OSError(code,'Unable to start MIDI input')
            time.sleep(seconds)
        finally:
            mm.midiInStop(handle);mm.midiInReset(handle);mm.midiInClose(handle)
        return dict(device=devices[device_id],events=events,truncated=len(events)>=4096,audition_feedback_verified=False)
