// Native session import through Adobe's published Session SDK, not XML guessing.
#include <windows.h>
#include <string>
#include <stdexcept>
#include <cmath>
#include <vector>
#include "AuditionSDK/ASDKString.h"
#include "AuditionSDK/Session/SessionInterfaceTemplate.h"
#include "AuditionSDK/Session/TrackType.h"

static const asdk::uniChar16* u(const wchar_t* s) { return reinterpret_cast<const asdk::uniChar16*>(s); }
class ControllerSession : public ases::SessionInterface {
    std::wstring file;
    std::wstring text(const std::wstring& section, const wchar_t* key, const wchar_t* fallback=L"") {
        wchar_t value[4096];
        DWORD n=GetPrivateProfileStringW(section.c_str(),key,fallback,value,4096,file.c_str());
        if(n>=4095)throw std::runtime_error("oversized value");
        return value;
    }
    double number(const std::wstring& section,const wchar_t* key,double fallback,double low,double high) {
        auto s=text(section,key);
        if(s.empty())return fallback;
        wchar_t* end=nullptr;double value=wcstod(s.c_str(),&end);
        if(!end||*end||!std::isfinite(value)||value<low||value>high)throw std::runtime_error("invalid number");
        return value;
    }
    ases::SessionResult GetPlugInInfo(ases::ISessionGetPlugInInfo* info) override {
        info->SetPluginID("E316D202-94AD-4ED3-9B47-9EA00EB8B645",u(L"Controller Native Session Bridge"));
        const asdk::uniChar16* extensions[]={u(L"auctl")};
        info->AddImportFormat(u(L"Controller Native Session"),extensions,1);
        return 0;
    }
    ases::SessionResult SessionOpen(ases::ISessionOpen* input) override {
        auto name=input->GetFileName();if(!name)return -6;
        file.assign(reinterpret_cast<const wchar_t*>(name->GetData()),name->GetLength());
        return text(L"session",L"format")==L"AU_CONTROLLER_1"?0:-8;
    }
    ases::SessionResult ReadSession(ases::IEditSession* session) override {
        try {
            const int count=(int)number(L"session",L"tracks",1,1,64);
            const int rate=(int)number(L"session",L"rate",48000,8000,192000);
            const int channels=(int)number(L"session",L"channels",2,1,6);
            if(channels!=1&&channels!=2&&channels!=6)return -6;
            session->SetSessionName(u(text(L"session",L"name",L"Controller Session").c_str()));
            session->SetSampleRate(rate);session->SetBitDepth(32);session->SetChannelCount(channels);
            session->SetMixingState(false,-3);
            auto master=session->AddAudioTrack(10000);
            master->SetTrackType(ases::kTrackType_Master);master->SetTrackOrder(count+2);
            master->SetTrackChannels(channels);master->SetTrackName(u(L"Master"));master->SetVisible(true);
            master->SetTrackOutputPortID(0);master->GetFaderComponent()->SetParameterValue(0,1);
            auto bus=session->AddAudioTrack(10090);
            bus->SetTrackType(ases::kTrackType_Bus);bus->SetTrackOrder(count+1);bus->SetTrackChannels(channels);
            bus->SetTrackName(u(L"Controller Send Bus"));bus->SetTrackOutputTrackID(10000);bus->SetVisible(true);
            bus->GetFaderComponent()->SetParameterValue(0,1);
            asdk::int64 duration=0;
            for(int i=0;i<count;i++) {
                std::wstring section=L"track"+std::to_wstring(i);
                std::wstring path=text(section,L"path");
                if(path.empty()||GetFileAttributesW(path.c_str())==INVALID_FILE_ATTRIBUTES)return -4;
                auto frames=(asdk::int64)number(section,L"frames",0,1,1e12);
                auto start=(asdk::int64)number(section,L"start",0,0,1e12);
                auto fileInfo=session->AddFileInfo(i);
                fileInfo->SetFilePath(u(path.c_str()));fileInfo->SetFileDuration(frames);fileInfo->SetMediaHandlerID(u(L"AmioWav"));
                auto track=session->AddAudioTrack(10001+i);
                track->SetTrackType(ases::kTrackType_Audio);track->SetTrackOrder(i+1);
                track->SetTrackChannels((asdk::uint32)number(section,L"channels",1,1,2));
                track->SetTrackName(u(text(section,L"name",L"Controller Track").c_str()));
                track->SetTrackOutputTrackID(10000);track->SetVisible(true);track->SetTrackArmedForRecord(false);
                track->SetAutomationMode(ases::kAutomationMode_Read);track->SetAutomationLaneOpenState(true);
                auto fader=track->GetFaderComponent();
                fader->SetParameterValue(0,(float)number(section,L"gain",1,0,1));
                track->GetPannerComponent()->SetParameterValue(0,(float)number(section,L"pan",0,-1,1));
                int points=(int)number(section,L"points",0,0,4096);
                if(points) {
                    auto keys=fader->GetEditKeyframeList(0);keys->SetSplinesEnable(false);
                    asdk::int64 previous=-1;
                    for(int j=0;j<points;j++) {
                        auto key=section+L"_point"+std::to_wstring(j);
                        auto sample=(asdk::int64)number(key,L"sample",0,0,1e12);
                        if(sample<=previous)return -6;previous=sample;
                        keys->AddKeyframe((float)number(key,L"value",1,0,1),sample,false,false);
                    }
                }
                double sendGain=number(section,L"send",0,0,1);
                if(sendGain>0) {
                    auto send=track->GetEditSendList()->AddSend();
                    send->SetSlotIndex(0);send->SetOutputTrackID(10090);send->SetPreFader(false);
                    send->GetEditSendComponent()->SetParameterValue(ases::kSendParameter_Power,1);
                    send->GetEditSendComponent()->SetParameterValue(ases::kSendParameter_Level,(float)sendGain);
                }
                const int effects=(int)number(section,L"effects",0,0,16);
                if(effects) {
                    auto rack=track->GetEditEffectsRack();rack->SetEffectsRackPreFader(false);
                    for(int effectIndex=0;effectIndex<effects;effectIndex++) {
                        auto effectSection=section+L"_effect"+std::to_wstring(effectIndex);
                        auto id=text(effectSection,L"component_id");
                        auto chunk=text(effectSection,L"chunk_hex");
                        if(id.empty()||chunk.size()%2)return -6;
                        std::vector<asdk::uint8> bytes;
                        for(size_t index=0;index<chunk.size();index+=2) {
                            wchar_t part[3]={chunk[index],chunk[index+1],0};wchar_t* end=nullptr;
                            auto byte=wcstoul(part,&end,16);if(!end||*end||byte>255)return -6;
                            bytes.push_back((asdk::uint8)byte);
                        }
                        auto effect=rack->AddEffect();effect->SetSlotIndex(effectIndex);effect->SetBypass(false);
                        auto component=effect->GetEditAudioComponent();
                        component->SetComponentID(u(id.c_str()));component->SetPowered(true);
                        if(!bytes.empty())component->SetChunkData(bytes.data(),(asdk::uint32)bytes.size());
                    }
                }
                auto clip=track->AddClip(i);
                clip->SetClipFileID(i);clip->SetClipStart(start);clip->SetClipInPoint(0);clip->SetClipDuration(frames);
                clip->SetClipName(u(text(section,L"name",L"Controller Clip").c_str()));clip->SetClipOffline(false);
                const int inputChannels=(int)number(section,L"channels",1,1,2);
                for(int ch=0;ch<inputChannels;ch++)clip->SetClipSourceChannel(ch,ch);
                clip->GetEditGainComponent()->SetParameterValue(0,1);
                duration=duration>start+frames?duration:start+frames;
                if(!session->UpdateProgress(i+1,count))return -1;
            }
            session->SetDuration(duration);
            return 0;
        } catch(...) { return -7; }
    }
};
extern "C" __declspec(dllexport) ases::SessionResult SessionInterface(asdk::int32 command,void* interfacePtr) {
    static ControllerSession bridge;
    try { return bridge.EntryPoint(command,interfacePtr); } catch(...) { return -7; }
}
