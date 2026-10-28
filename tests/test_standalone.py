import os
os.environ["FACEBOOK_ENABLED"] = "0"
os.environ["WEB_AI_ENABLED"] = "0"

import unittest
from unittest.mock import patch
import requests
import app as bot
import standalone as web


class StandaloneTests(unittest.TestCase):
    def setUp(self):
        web._limits.clear()
        web._chapter_cache.clear()
        self.client = bot.app.test_client()
        self.answer = bot.app.extensions["web_answer"]
        self.parse = bot.app.extensions["web_parse_reference"]
        # Any accidental external POST (including Facebook) fails the test.
        self.network = patch.object(requests, "post", side_effect=AssertionError("unexpected outbound post"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_site_and_assets(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'og:image',r.data)
        with self.client.get('/static/chat.js') as asset:
            self.assertIn(b'/api/',asset.data)
        for path in ('/health','/status','/chat-privacy','/static/share-card.png','/static/arabic.ttf'):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code,200,path)

    def test_preserves_schedule_and_address(self):
        self.assertEqual(self.answer("موعد الاجتماع", "ar")["answer"],bot.service_time_text())
        self.assertEqual(self.answer("العنوان", "ar")["answer"],bot.address_text())

    def test_address_and_google_maps_are_visible_without_chat(self):
        with patch.object(bot, 'ADDRESS', 'عنوان الكنيسة المخصص'), patch.object(bot, 'MAPS_URL', 'https://maps.app.goo.gl/test-map'):
            page=self.client.get('/').text
        self.assertIn('عنوان الكنيسة المخصص',page)
        self.assertIn('id="church-map" href="https://maps.app.goo.gl/test-map"',page)
        self.assertIn('class="composer-label"',page)

    def test_theological_where_when_not_church_details(self):
        for text in ('متى يرجع المسيح؟','وين ولد يسوع؟','When will Christ return?','Where was Jesus born?'):
            result=self.answer(text,'ar')
            self.assertEqual(result['topic'],'unknown',text)
            self.assertNotIn('10:30',result['answer'])
            self.assertNotIn(bot.ADDRESS,result['answer'])

    @patch('standalone.chapter_text', return_value=({6:'EXACT VERIFIED SOURCE TEXT',16:'EXACT SECOND SOURCE TEXT'},'https://ebible.org/arb-vd/JHN03.htm'))
    def test_colloquial_jesus_question(self, chapter):
        result=self.answer('مين هو يسوع؟','ar')
        self.assertEqual(result['topic'],'jesus')
        self.assertEqual(result['verses'][0]['text'],'EXACT VERIFIED SOURCE TEXT')

    def test_references_both_languages_and_digits(self):
        for text,expected in [('John 3:16',('JHN',3,16,16)),('يوحنا٣:١٦',('JHN',3,16,16)),('1 John 1:9',('1JN',1,9,9)),('2 Timothy 3:16-17',('2TI',3,16,17)),('مزمور ٢٣',('PSA',23,None,None))]:
            self.assertEqual(self.parse(text),expected,text)
        self.assertIsNone(self.parse('John 3:0'))
        self.assertIsNone(self.parse('John 3:20-16'))

    @patch('standalone.chapter_text',side_effect=requests.Timeout())
    def test_no_generated_verse_when_ebible_unavailable(self,chapter):
        result=self.answer('John 3:16','en')
        self.assertTrue(result['verses'][0]['unavailable'])
        self.assertNotIn('For God so loved',result['verses'][0]['text'])

    @patch('standalone.chapter_text', return_value=({16:'For God so loved the world'},'https://ebible.org/eng-kjv/JHN03.htm'))
    def test_english_uses_kjv(self,chapter):
        r=self.client.post('/api/chat',json={'message':'John 3:16','lang':'en'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['verses'][0]['translation'],'KJV')
        self.assertEqual(chapter.call_args.args,('JHN',3,'en'))

    def test_webhook_does_not_answer_facebook(self):
        with patch.object(bot,'handle_message') as handler,patch.object(bot,'handle_feed_change') as comments:
            data={'object':'page','entry':[{'messaging':[{'sender':{'id':'x'},'message':{'text':'hello'}}],'changes':[{'field':'feed'}]}]}
            self.assertEqual(self.client.post('/webhook',json=data).status_code,200)
            handler.assert_not_called()
            comments.assert_not_called()
        self.assertEqual(self.client.get('/setup').status_code,403)

    def test_prayer_is_not_claimed_delivered(self):
        result=self.answer('طلب صلاة','ar')
        self.assertIn('لا ترسل',result['answer'])
        self.assertNotIn('رسالتك وصلت',result['answer'])

    def test_no_verse_for_greeting(self):
        self.assertEqual(self.answer('سلام','ar')['verses'],[])

    @patch('standalone.chapter_text', return_value=({n:'SOURCE VERSE' for n in range(1,177)},'https://ebible.org/arb-vd/JHN03.htm'))
    def test_normal_arabic_questions_support_definite_article(self, chapter):
        self.assertEqual(self.answer('ما هي المعمودية؟','ar')['topic'],'baptism')
        self.assertEqual(self.answer('كيف أنال الخلاص؟','ar')['topic'],'salvation')

    def test_unknown_does_not_claim_inbox_delivery(self):
        result=self.answer('سؤال غير موجود بالمكتبة','ar')
        self.assertIn('لم يُرسَل',result['answer'])

    @patch('standalone.chapter_text', return_value=({n:'SOURCE VERSE' for n in range(1,177)},'https://ebible.org/arb-vd/JHN03.htm'))
    def test_topic_prose_has_no_empty_scripture_lead_ins(self, chapter):
        result=self.answer('كيف أخلص؟','ar')
        self.assertEqual(result['topic'],'salvation')
        self.assertNotIn('ببساطة: .',result['answer'])
        self.assertNotIn('\n.\n',result['answer'])
        self.assertTrue(result['verses'])

    def test_api_validation_and_origin(self):
        for data in ([],None,{'message':4},{'message':'x'*1501},{'message':'x','lang':'bad'},{'message':'x','action':'setup'}):
            r=self.client.post('/api/chat',json=data)
            self.assertIn(r.status_code,(400,415))
        r=self.client.post('/api/chat',json={'message':'hello'},headers={'Origin':'https://other.example'})
        self.assertEqual(r.status_code,403)

    def test_rate_limit(self):
        for _ in range(20):
            self.assertEqual(self.client.post('/api/chat',json={'message':'hello'}).status_code,200)
        self.assertEqual(self.client.post('/api/chat',json={'message':'hello'}).status_code,429)

    def test_no_html_interpolation_in_client(self):
        with self.client.get('/static/chat.js') as response:
            script=response.text
        self.assertNotIn('innerHTML',script)
        self.assertNotIn('localStorage',script)

    def test_missing_verify_token_is_not_500(self):
        self.assertEqual(self.client.get('/webhook?hub.mode=subscribe').status_code,403)

    def test_unconfigured_meta_verification_is_rejected(self):
        with patch.object(bot, 'VERIFY_TOKEN', ''):
            self.assertEqual(self.client.get('/webhook?hub.mode=subscribe&hub.verify_token=').status_code,403)

    def test_configured_meta_verification(self):
        with patch.object(bot, 'VERIFY_TOKEN', 'unit-test-token'):
            response=self.client.get('/webhook?hub.mode=subscribe&hub.verify_token=unit-test-token&hub.challenge=challenge')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.text,'challenge')

    def test_parser_retains_paragraphs_and_excludes_notes(self):
        p=web.VerseHTML()
        p.feed('<span class="verse" id="V16">16 </span><span class="wj">Exact <span>text</span>.</span></div><div class="p"> Continued.<a class="noteref">note</a><span class="verse" id="V17">17 </span>Next.<ul class="tnav"><li>navigation</li></ul>')
        self.assertEqual(p.result(),{16:'Exact text. Continued.',17:'Next.'})


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        web._limits.clear()
        self.answer=bot.app.extensions['web_answer']

    @patch.dict(os.environ,{'WEB_AI_ENABLED':'1'})
    @patch.object(bot,'GROQ_KEY','fake-key')
    @patch('standalone.requests.post')
    def test_model_cannot_inject_displayed_answer(self,post):
        post.return_value.json.return_value={'choices':[{'message':{'content':'{"topic":"unknown","answer":"Invented Bible quotation John 99:99"}'}}]}
        result=self.answer('A completely unknown question','en')
        self.assertNotIn('Invented',str(result))
        self.assertEqual(result['verses'],[])

    @patch.dict(os.environ,{'WEB_AI_ENABLED':'1'})
    @patch.object(bot,'GROQ_KEY','fake-key')
    @patch('standalone.requests.post')
    def test_model_cannot_route_bible_event_to_church_schedule(self,post):
        post.return_value.json.return_value={'choices':[{'message':{'content':'{"topic":"schedule"}'}}]}
        self.assertEqual(self.answer('متى يرجع المسيح؟','ar')['topic'],'unknown')


if __name__=='__main__':
    unittest.main()
