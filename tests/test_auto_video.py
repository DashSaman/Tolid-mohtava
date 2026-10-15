import unittest,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from video_edit import educational_silence_cuts,semantic_decisions,validate_zooms,plan_fingerprint
from captions import retime_captions,export_captions
from auto_video import validate_plan,AutoEditPlans

class EducationalEditingTests(unittest.TestCase):
    def test_similar_but_different_commands_and_negation_survive(self):
        for a,b in [('Run sudo systemctl restart nginx to apply the new configuration','Run sudo systemctl reload nginx to apply the new configuration'),
                    ('این تنظیمات شبکه را باید حتما ذخیره کنید','این تنظیمات شبکه را نباید حتما ذخیره کنید'),
                    ('Run command alpha && beta for this network','Run command alpha || beta for this network')]:
            segments=[{'start':0,'end':2,'text':a},{'start':5,'end':7,'text':b}]
            self.assertEqual(semantic_decisions([{'segment':0,'duplicate_of':1,'confidence':.99}],segments,60),[])
    def test_existing_cut_cannot_remove_the_referenced_duplicate_take(self):
        segments=[{'start':0,'end':3,'text':'این جمله برای تنظیم شبکه کاملا یکسان است'},{'start':5,'end':8,'text':'این جمله برای تنظیم شبکه کاملا یکسان است'}]
        self.assertEqual(semantic_decisions([{'segment':0,'duplicate_of':1,'confidence':1}],segments,60,existing_cuts=[(5,8)]),[])
    def test_duplicate_cycles_and_chains_keep_the_referenced_take(self):
        segments=[{'start':i*5,'end':i*5+2,'text':'این یک جمله تکراری برای آموزش شبکه است'} for i in range(3)]
        decisions=semantic_decisions([{'segment':0,'duplicate_of':1,'confidence':1},
            {'segment':1,'duplicate_of':0,'confidence':1},{'segment':2,'duplicate_of':0,'confidence':1}],segments,60)
        removed={d['segment'] for d in decisions}
        self.assertTrue(decisions)
        self.assertTrue(all(d['duplicate_of'] not in removed for d in decisions))
    def test_silence_keeps_breathing_room_and_preserves_instruction_pause(self):
        segments=[{'start':0,'end':2,'text':'تنظیمات را ذخیره کنید'}, {'start':8,'end':10,'text':'منتظر بمانید تا سرویس راه‌اندازی شود'}]
        cuts=educational_silence_cuts([(2,7,5),(10,15,5)],segments,20)
        self.assertTrue(cuts)
        self.assertGreaterEqual(cuts[0][0],2.18)
        self.assertLessEqual(cuts[0][1],6.82)
        self.assertFalse(any(s<15 and e>10 for s,e in cuts),'waiting for a service must survive')
    def test_short_pauses_and_silent_screen_activity_are_preserved(self):
        self.assertEqual(educational_silence_cuts([(2,3,1)],[],10),[])
        self.assertEqual(educational_silence_cuts([(2,7,5)],[],10,activity=[(3,6)]),[])
    def test_ai_cannot_delete_changed_ip_or_unique_instruction(self):
        segments=[{'start':0,'end':3,'text':'آدرس 192.168.1.1 را وارد کنید'}, {'start':4,'end':7,'text':'آدرس 192.168.2.1 را وارد کنید'}, {'start':8,'end':11,'text':'تنظیمات را ذخیره کنید'}]
        proposals=[{'segment':1,'duplicate_of':0,'confidence':.99,'reason':'repeat'},{'segment':2,'duplicate_of':0,'confidence':.99,'reason':'repeat'}]
        self.assertEqual(semantic_decisions(proposals,segments,15),[])
    def test_repeated_take_cuts_earlier_copy_and_retains_complete_take(self):
        segments=[{'start':0,'end':3,'text':'برای نصب تنظیمات شبکه را باز کنید'}, {'start':4,'end':7,'text':'برای نصب تنظیمات شبکه را باز کنید'}]
        decisions=semantic_decisions([{'segment':0,'duplicate_of':1,'confidence':.96,'reason':'repeat'}],segments,30)
        self.assertEqual(len(decisions),1)
        self.assertLess(decisions[0]['end'],4)
    def test_unknown_segments_low_confidence_and_unbounded_cut_budget_rejected(self):
        segments=[{'start':0,'end':8,'text':'این یک جمله تکراری برای آموزش است'}, {'start':9,'end':17,'text':'این یک جمله تکراری برای آموزش است'}]
        proposals=[{'segment':10,'duplicate_of':1,'confidence':1},{'segment':0,'duplicate_of':1,'confidence':.2},{'segment':0,'duplicate_of':1,'confidence':1}]
        self.assertEqual(semantic_decisions(proposals,segments,20),[])
    def test_invalid_visual_regions_do_not_become_zoom_filters(self):
        regions=[{'start':1,'end':3,'box':[-1,0,.2,.2],'confidence':1},{'start':1,'end':3,'box':[.8,.8,.5,.5],'confidence':1}]
        self.assertEqual(validate_zooms(regions,10),[])
        accepted=validate_zooms([{'start':1,'end':3,'box':[.2,.2,.3,.3],'confidence':.95}],10)
        self.assertEqual(len(accepted),1);self.assertLessEqual(accepted[0]['scale'],1.3)
    def test_final_snapshot_changes_when_timeline_or_caption_options_change(self):
        first=plan_fingerprint('raw-sha',1,[(2,3)],{'subtitles':True},[])
        self.assertNotEqual(first,plan_fingerprint('raw-sha',2,[(2,3)],{'subtitles':True},[]))
        self.assertNotEqual(first,plan_fingerprint('raw-sha',1,[(2,4)],{'subtitles':True},[]))

class CaptionTimingTests(unittest.TestCase):
    def test_word_captions_follow_cuts_and_exclude_removed_filler(self):
        segs=[{'start':0,'end':5,'text':'سلام اِ شبکه','words':[{'start':0,'end':1,'word':'سلام'},{'start':2,'end':3,'word':'اِ'},{'start':4,'end':5,'word':'شبکه'}]}]
        cues=retime_captions(segs,[(0,2),(3,5)])
        self.assertEqual(' '.join(c['text'] for c in cues),'سلام شبکه')
        self.assertAlmostEqual(cues[-1]['end'],4)
    def test_crossing_caption_is_clipped_and_long_pause_not_covered(self):
        cues=retime_captions([{'start':1,'end':5,'text':'آموزش شبکه'}],[(0,2),(4,6)])
        self.assertEqual([(c['start'],c['end']) for c in cues],[(1,2),(2,3)])
    def test_srt_rounding_carries_into_next_second_and_ass_commands_are_plain_text(self):
        cue=[{'start':1.9996,'end':3.001,'text':'تنظیمات {\\pos(1,1)}'}]
        srt=export_captions(cue,'srt');self.assertIn('00:00:02,000',srt);self.assertNotIn(',1000',srt)
        ass=export_captions(cue,'ass');self.assertNotIn('{\\pos',ass)

class ReviewSnapshotTests(unittest.TestCase):
    def test_manual_mutation_is_blocked_while_background_edit_holds_media(self):
        from types import SimpleNamespace
        from auto_video import locked_handler,edit_mutation
        ctx=SimpleNamespace(payload={'media_id':'concurrent-fixture'},cancelled=lambda:False)
        def background(_):
            with self.assertRaisesRegex(ValueError,'در حال اجرا'):
                with edit_mutation('concurrent-fixture'):pass
            return 'finished'
        self.assertEqual(locked_handler(background)(ctx),'finished')
        with edit_mutation('concurrent-fixture'):pass
    def test_final_rejects_new_transcript_or_changed_cuts(self):
        media={'id':'m','sha256':'raw','content_id':'c'};transcript={'revision':1}
        plan={'media_id':'m','raw_sha':'raw','transcript_revision':1,'cuts':[[2,3]],'options':{},'zooms':[]}
        plan['fingerprint']=plan_fingerprint('raw',1,plan['cuts'],{},[])
        validate_plan(plan,media,transcript,[(2,3)])
        with self.assertRaises(ValueError):validate_plan(plan,media,{'revision':2},[(2,3)])
        with self.assertRaises(ValueError):validate_plan(plan,media,transcript,[(2,4)])
    def test_plan_and_caption_metadata_survive_restart(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'plans.sqlite';plans=AutoEditPlans(db)
            row=plans.save({'media_id':'media','raw_sha':'raw','transcript_revision':2,'cuts':[],'options':{'subtitles':True},'zooms':[]})
            self.assertEqual(AutoEditPlans(db).latest('media')['id'],row['id'])

class WordTimestampTests(unittest.TestCase):
    def test_whisper_requests_and_preserves_real_word_timestamps(self):
        from types import SimpleNamespace
        from transcribe import _transcribe_with
        class Engine:
            def transcribe(self,path,**kwargs):
                self.options=kwargs
                word=SimpleNamespace(start=.1,end=.4,word=' سلام',probability=.98)
                return iter([SimpleNamespace(start=0,end=1,text='سلام',words=[word])]),SimpleNamespace(duration=1)
        model=Engine();segments,_=_transcribe_with(model,'source.mp4')
        self.assertTrue(model.options.get('word_timestamps'))
        self.assertEqual(segments[0]['words'][0]['word'],'سلام')
        self.assertEqual(segments[0]['words'][0]['end'],.4)

class LocalVisionTests(unittest.TestCase):
    def test_tiny_cursor_activity_preserves_silent_instruction_window(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from visual_edit import screen_activity
        black=bytes(96*54);cursor=bytes([255])+black[1:]
        ctx=SimpleNamespace(cancelled=lambda:False)
        with patch('visual_edit.gray_frame',side_effect=[black,cursor,cursor,cursor]):
            self.assertEqual(screen_activity('screen.mp4',[(0,3,3)],ctx),[(0,3)])
    def test_named_region_coordinates_are_validated_after_local_image_request(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        from visual_edit import zoom_proposals
        ai=Mock(provider_for_task=lambda _: {'base_url':'http://127.0.0.1:11434/v1'})
        ctx=SimpleNamespace(cancelled=lambda:False,log=lambda _:None)
        response={'content':'{"box":{"x":0.15,"y":0.2,"width":0.7,"height":0.6},"confidence":0.95,"reason":"تنظیمات شبکه"}'}
        with patch('visual_edit.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=b'fixture-jpeg')),patch('visual_edit.chat',return_value=response) as chat:
            zooms=zoom_proposals('fixture.mp4',24,[{'start':8,'end':10,'text':'پنجره تنظیمات'}],ai,ctx)
        self.assertEqual(len(zooms),1)
        self.assertEqual(zooms[0]['box'],[.15,.2,.7,.6])
        messages=chat.call_args.args[2];self.assertTrue(messages[0]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,'))

class FinalPipelineTests(unittest.TestCase):
    def test_approval_gate_and_shorts_use_reviewed_final_timeline(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        from auto_video import auto_edit_final_handler
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'test.sqlite'
            media={'id':'m','sha256':'raw','path':'raw.mp4','duration':60}
            transcript={'revision':1,'segments':[{'start':20,'end':25,'text':'چگونه تنظیمات شبکه را به درستی وارد کنیم و نتیجه را بررسی کنیم؟'}]}
            plan=AutoEditPlans(db).save({'media_id':'m','raw_sha':'raw','transcript_revision':1,'cuts':[[1,6]],
                'options':{'shorts':True},'zooms':[],'preview_id':'preview','source_duration':60})
            services={'store':SimpleNamespace(path=db),'media':Mock(get=lambda _:media,verify=lambda _:True),
                'transcripts':Mock(get=lambda _:transcript),'decisions':Mock(timeline=lambda _:[(1,6)]),
                'renders':Mock(get=lambda _:{'path':'final-reviewed.mp4'})}
            ctx=SimpleNamespace(id='j',payload={'plan_id':plan['id']},services=services,
                log=lambda _:None,progress=lambda _:None,cancelled=lambda:False)
            with patch('video_render.render_educational',return_value={'render_id':'final','duration':55}) as render,patch('shorts.render_short_handler',return_value={'render_id':'short'}) as short:
                self.assertTrue(auto_edit_final_handler(ctx)['waiting_approval']);render.assert_not_called()
                ctx.payload['approved']=True;result=auto_edit_final_handler(ctx)
                self.assertEqual(result['shorts'],[{'render_id':'short'}])
                sub=short.call_args.args[0]
                self.assertEqual(sub.payload['start'],15)
                self.assertEqual(sub.services['media'].get('m')['path'],'final-reviewed.mp4')
                services['transcripts']=Mock(get=lambda _:{'revision':2})
                with self.assertRaises(ValueError):auto_edit_final_handler(ctx)
                self.assertEqual(render.call_count,1)

class RealEducationalRenderTests(unittest.TestCase):
    def test_many_fractional_cuts_keep_video_audio_and_caption_timeline_aligned(self):
        import avtools,subprocess,json
        from types import SimpleNamespace
        from render import Renders
        from video_render import render_educational
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'source.mp4';keep=[(i*2+.017,i*2+1.067) for i in range(12)]
            cuts=[(0,keep[0][0])]+[(b,keep[i+1][0]) for i,(_,b) in enumerate(keep[:-1])]+[(keep[-1][1],24)]
            run=subprocess.run([avtools.ffmpeg_path(),'-y','-f','lavfi','-i',"color=c=black:s=160x90:r=30:d=24,drawbox=color=white:t=fill:enable='between(mod(t,2),0.5,0.6)'",
                '-f','lavfi','-i',"aevalsrc=sin(2*PI*660*t)*between(mod(t\\,2)\\,0.5\\,0.6):s=8000:d=24",'-c:v','libx264','-c:a','aac','-shortest',str(src)],capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr.decode('utf-8','replace'))
            rd=Renders(root/'db.sqlite',root/'renders');ctx=SimpleNamespace(id='j',services={'renders':rd},log=lambda _:None,progress=lambda _:None,cancelled=lambda:False)
            plan={'cuts':cuts,'zooms':[],'options':{'subtitles':False,'denoise':False}}
            result=render_educational(ctx,{'id':'m','path':str(src),'sha256':'fixture'},{'revision':1,'segments':[]},plan,'preview',nvenc=False)
            out=rd.get(result['render_id'])['path'];probe=subprocess.run([avtools.ffprobe_path(),'-v','error','-show_streams','-of','json',out],capture_output=True,check=True)
            streams=json.loads(probe.stdout)['streams'];v=next(s for s in streams if s['codec_type']=='video');a=next(s for s in streams if s['codec_type']=='audio')
            self.assertAlmostEqual(float(v['duration']),12.6,delta=.04)
            self.assertAlmostEqual(float(a['duration']),12.6,delta=.04)
            self.assertAlmostEqual(float(v['duration']),float(a['duration']),delta=.04)
            video=subprocess.run([avtools.ffmpeg_path(),'-v','error','-i',out,'-an','-pix_fmt','gray','-f','rawvideo','-'],capture_output=True,check=True).stdout
            audio=subprocess.run([avtools.ffmpeg_path(),'-v','error','-i',out,'-vn','-ac','1','-ar','8000','-f','s16le','-'],capture_output=True,check=True).stdout
            import array
            samples=array.array('h');samples.frombytes(audio)
            visible=[i/30 for i in range(len(video)//(160*90)) if sum(video[i*14400:(i+1)*14400])/14400>100]
            audible=[i/8000 for i in range(0,len(samples),80) if max(abs(x) for x in samples[i:i+80])>4000]
            for i in range(12):
                expected=i*1.05+.483
                vmark=min(t for t in visible if expected-.1<t<expected+.2)
                amark=min(t for t in audible if expected-.1<t<expected+.2)
                self.assertAlmostEqual(vmark,amark,delta=.06,msg=f'marker {i} drifted')
    def test_real_video_cuts_zoom_captions_audio_and_unchanged_raw(self):
        import avtools,subprocess,hashlib
        from types import SimpleNamespace
        from render import Renders,probe_duration
        from video_render import render_educational,probe_streams
        if not avtools.ffmpeg_path():self.skipTest('FFmpeg unavailable')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'raw.mp4'
            subprocess.run([avtools.ffmpeg_path(),'-y','-f','lavfi','-i','testsrc2=size=320x180:rate=10:duration=4.1',
                '-f','lavfi','-i','sine=frequency=660:duration=4.1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(src)],capture_output=True,check=True,timeout=30)
            before=hashlib.sha256(src.read_bytes()).hexdigest();rd=Renders(root/'render.sqlite',root/'renders')
            ctx=SimpleNamespace(id='fixture',services={'renders':rd},log=lambda _:None,progress=lambda _:None,cancelled=lambda:False)
            media={'id':'media','path':str(src),'sha256':before};transcript={'revision':1,'segments':[{'start':2.5,'end':3.5,'text':'آموزش شبکه'}]}
            plan={'id':'plan','cuts':[(1,2)],'options':{'subtitles':True,'denoise':True},'zooms':[{'start':2,'end':3,'scale':1.25,'center_x':.5,'center_y':.5}]}
            result=render_educational(ctx,media,transcript,plan,'preview',nvenc=False)
            out=Path(rd.get(result['render_id'])['path']);streams=probe_streams(out)
            self.assertTrue(streams['video'] and streams['audio']);self.assertAlmostEqual(probe_duration(out),3.1,delta=.12)
            self.assertIn('00:00:01,500',out.with_suffix('.srt').read_text(encoding='utf-8'))
            self.assertTrue(out.with_suffix('.ass').exists());self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(),before)
            def reject_stale():raise ValueError('stale edit snapshot')
            before_files=set((rd.root/'media').iterdir())
            with self.assertRaisesRegex(ValueError,'stale'):
                render_educational(ctx,media,transcript,plan,'final',nvenc=False,before_register=reject_stale)
            self.assertEqual(len(rd.list('media')),1,'rejected finals must never become visible')
            self.assertEqual(set((rd.root/'media').iterdir()),before_files)
    def test_stream_probe_distinguishes_video_without_audio(self):
        import avtools,subprocess
        from video_render import probe_streams
        if not avtools.ffmpeg_path():self.skipTest('FFmpeg unavailable')
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'silent.mp4'
            subprocess.run([avtools.ffmpeg_path(),'-y','-f','lavfi','-i','color=s=160x90:d=0.3','-an',str(src)],capture_output=True,check=True,timeout=30)
            self.assertFalse(probe_streams(src)['audio'])

if __name__=='__main__':unittest.main()
