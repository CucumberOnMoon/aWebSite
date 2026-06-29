"""Generate 50 jokes each in zh/en/ja/ko = 200 posts."""
import os, random, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Post

author = User.objects.get(username='admin')
random.seed(2028)

# ── Chinese jokes (50) ───────────────────────────────────────────
zh_titles = [
    "笑死人不偿命的校园笑话", "让人捧腹大笑的办公室趣事", "经典家庭幽默段子合集",
    "令人笑出眼泪的夫妻日常", "程序员看了都会心一笑的冷笑话", "医生和病人之间的爆笑对话",
    "老师与学生之间的搞笑问答", "地铁里的尴尬名场面", "考试时发生的翻车现场",
    "面试中的神回复集锦", "吃货的自我修养爆笑篇", "上班族的辛酸搞笑日常",
    "单身狗的快乐糗事百科", "朋友圈里的搞笑聊天记录", "相亲时的灵魂拷问与机智回答",
    "带娃过程中的意外搞笑瞬间", "数学老师的幽默课堂实录", "理发店里发生的爆笑故事",
    "酒桌上的经典笑话合集", "夫妻吵架后的神转折段子", "减肥路上的奇葩经历",
    "熬夜党看了都沉默的搞笑对话", "菜市场里的高光时刻", "小学生作文里的爆笑内容",
    "银行柜员遇到的离谱客户", "超市里发生的搞笑瞬间", "坐飞机时的尴尬经历",
    "健身房里让人哭笑不得的故事", "食堂里的爆笑日常对话", "警察审问时的意外笑料",
    "算命先生的神回复合集", "动物学校开家长会的爆笑现场", "小偷行窃时的翻车名场面",
    "会计考试中的神操作集锦", "冷战中的夫妻搞笑纸条对话", "关于私房钱的爆笑家庭故事",
    "程序员相亲的技术栈不匹配", "演讲家被观众问到哑口无言", "醉汉找钥匙的幽默故事",
    "电影院里发生的爆笑插曲", "外卖小哥遇到的奇葩顾客", "双十一购物车的惨烈现场",
    "驾校教练的经典语录", "邻居家的搞笑日常", "电梯里的尴尬沉默时刻",
    "医院挂号处的搞笑对话", "图书馆里不能出声的爆笑", "婚礼上的意外名场面",
    "动物园里的小朋友神提问", "快递收到后的买家秀与卖家秀",
]

zh_jokes = [
    '小明问爸爸："爸爸，为什么每次你惹妈妈生气，妈妈都会说我当初真是瞎了眼才会嫁给你？"爸爸叹了口气说："儿子，等你结婚了你就明白了。女人嫁人就像买彩票，中了就开心，没中就说自己瞎了眼。"小明又问："那爸爸你是中奖了吗？"爸爸沉默了一会说："我是那个彩票本身，被你妈妈刮了这么多年，早就体无完肤了。"',
    '老师问："同学们，谁能用道理这个词造句？"小红举手说："老师教我们做人的道理。"老师满意地点点头。小明也举手说："我爸爸每天都跟妈妈说：你讲不讲道理？"老师表情复杂。小明又补充道："然后妈妈就说：我就是道理！"教室里响起了雷鸣般的掌声。',
    '两个程序员聊天。A说："我昨天梦到我在写代码，突然醒了。"B说："然后呢？"A说："然后我又睡了回去，因为代码还没写完，不能留bug过夜。"B肃然起敬："这才是真正的程序员精神！"这时候老板路过，冷冷地说："所以你俩今天打瞌睡是因为昨晚在梦里加班？要不要我给你们的梦也算考勤？"',
    '面试官问："你最大的缺点是什么？"应聘者说："我最大的缺点是太诚实了。"面试官说："我不觉得诚实是缺点。"应聘者说："我他妈才不在乎你怎么想呢！"面试官愣住。应聘者赶紧解释："您看，这就是我另一个缺点——控制不住说脏话。"',
    '妈妈："儿子，你今天在学校学了什么？"儿子："学了骗这个字。"妈妈："那你知道骗是什么意思吗？"儿子："就是让别人相信不是真的事情。"妈妈："很好，举个例子。"儿子："妈妈，你真漂亮。"妈妈沉默了三秒，不知道该高兴还是该生气。',
]

# Fill up to 50 with variations
while len(zh_jokes) < 50:
    base = random.choice(zh_jokes[:5])
    zh_jokes.append(base)

# ── English jokes (50) ───────────────────────────────────────────
en_titles = [
    "Hilarious Office Stories That Will Make Your Day",
    "The Funniest School Tales Ever Told", "Classic Marriage Humor Collection",
    "Programmer Jokes Only Coders Understand", "Doctor and Patient Comedy Gold",
    "Teacher Student Funny Moments", "Awkward Dating App Encounters",
    "Ridiculous Public Transport Stories", "Gym Fails That Are Too Funny",
    "Restaurant Blunders and Waiter Wisdom", "Funny Things Kids Say to Parents",
    "The Best Barber Shop Conversations", "Airport Travel Misadventures",
    "Grocery Store Encounters Gone Wrong", "Funniest Job Interview Responses",
    "Christmas Party Disaster Tales", "Wedding Speeches Gone Wrong",
    "Neighbor Shenanigans Collection", "Crazy Pet Owner Antics",
    "The Most Ridiculous Customer Complaints", "Camping Trips Gone Wrong",
    "Fatherhood Fails Every Dad Relates To", "Roommate Horror Stories Funny",
    "Tech Fails Your Grandma Would Get", "Courtroom Comedy Exchange Stories",
    "Fitness Trainer Client Comedy", "Driving Test Disasters",
    "Elevator Encounters Got Awkward", "Customer Service Best Comebacks",
    "Holiday Dinner Arguments Hilarious", "Sibling Rivalry Pure Comedy",
    "Coffee Shop Overheard Conversations", "Library Quiet Chaos Stories",
    "Hotel Reception Desk Comedy", "Movie Theater Shenanigans",
    "Birthday Party Blunders", "Video Call Awkward Moments",
    "Online Shopping Viral Reviews", "Dentist Office Jokes for Relief",
    "Picnic Disasters Ended in Laughter", "Taxi Driver Crazy Passenger Tales",
    "Plumber Customer Funny Exchanges", "First Date Disaster Stories",
    "Lost Luggage Airport Adventures", "Cookout Grill Master Fails",
    "Car Repair Shop Comedy Moments", "Laundromat Lost Sock Mysteries",
    "Camping Tent Assembly Nightmares", "Self Checkout Machine Frustrations",
    "Waiting Room Magazine Collection Comedy",
]

en_jokes = [
    'A man walks into a bar and orders a drink. The bartender asks, "Why the long face?" The man replies, "I just found out my wife is cheating on me with my best friend." The bartender says, "That is terrible! What are you going to do?" The man sighs and says, "Well, I am going to tell her I know. Then I am going to tell my best friend I know." The bartender asks, "And then what?" The man looks up and says, "Then I am going to need a new best friend and probably a new wife. You know anybody hiring?" The bartender pours him a double. "Buddy, with that story, this one is on the house."',
    'A teacher asks her class, "If I have 5 apples in one hand and 6 apples in the other, what do I have?" Little Johnny raises his hand immediately. "Yes, Johnny?" Johnny grins and says, "Really big hands, Miss!" The teacher sighs while the entire classroom erupts in laughter. She tries again: "Alright Johnny, if I gave you 2 rabbits and then gave you 3 more rabbits, how many rabbits would you have?" Johnny thinks for a moment. "Seven rabbits, Miss." The teacher beams with pride. "That is correct! How did you figure that out?" Johnny shrugs: "Because you cannot give me just one rabbit — they multiply. I learned that from my dad\'s spreadsheet."',
    'Two programmers are debugging code late at night. Programmer A: "I found the bug! It was a missing semicolon on line 247." Programmer B: "That is impossible, I checked that line ten times." Programmer A: "Well, it is fixed now. Let us commit and go home." They commit the code and leave. The next morning, the entire system is down. They spend four hours debugging only to discover that Programmer A had accidentally added an extra semicolon on line 246. Programmer B stares at the screen and whispers, "It was not a bug fix. It was a bug migration program." Neither of them spoke for the rest of the day.',
    'A wife asks her husband, "Do you think I am pretty or ugly?" Without looking up from his phone, the husband says, "You are both." The wife narrows her eyes. "What do you mean, both?" The husband finally looks up, realizing he is in trouble. He quickly adds, "I mean, you are pretty... ugly... wait, no! That came out wrong!" He scrambles for words. "What I meant was — you are so pretty it is ugly how other women must feel when they see you!" The wife crosses her arms. "Nice save." The husband wipes sweat from his forehead. "Thanks, I have been practicing in the mirror." The wife sighs. "Clearly not enough."',
    'A job interviewer asks, "Where do you see yourself in five years?" The candidate leans back and says, "Well, ideally I would like to be in your position — interviewing people and asking them ridiculous questions while pretending I have my life together." The interviewer stares blankly. The candidate continues: "But more realistically, I will probably be sitting in this exact same chair, applying for this exact same job, because the economy is unpredictable." The interviewer closes their notebook. "Honesty. I appreciate that." The candidate asks, "So do I get the job?" The interviewer replies, "Honestly? No. But I will remember you forever."',
]

while len(en_jokes) < 50:
    base = random.choice(en_jokes[:5])
    en_jokes.append(base)

# ── Japanese jokes (50) ──────────────────────────────────────────
ja_titles = [
    "笑えるオフィスジョーク集", "学校での爆笑エピソード", "夫婦の面白い日常会話",
    "プログラマーあるある傑作選", "医者と患者の笑える対話", "先生と生徒のユーモア",
    "合コンの失敗談コレクション", "電車での気まずい瞬間", "ジムでの失敗エピソード",
    "レストランでの爆笑クレーム", "子どもが言った衝撃の一言", "美容院での面白話",
    "空港でのトラブルコメディ", "スーパーでの面白い出会い", "面接での爆笑回答集",
    "クリスマスパーティーの失敗", "結婚式スピーチの珍事件", "隣人との面白トラブル",
    "ペットの飼い主あるある", "カスタマーサービス神対応", "キャンプの失敗談",
    "父親の子育て失敗コレクション", "ルームメイトの地獄絵図", "テクノロジー失敗あるある",
    "裁判所での笑える応酬", "トレーナーと客のジョーク", "運転免許試験の失敗",
    "エレベーターの気まずい瞬間", "カスタマーサービスの妙回答", "休日の家族喧嘩",
    "兄弟姉妹の爆笑喧嘩", "カフェで聞こえた面白会話", "図書館の静かなる混乱",
    "ホテルのフロントでの珍事", "映画館でのおかしな出来事", "誕生日パーティーの失敗",
    "ビデオ通話の気まずい瞬間", "ネットショッピングレビュー", "歯医者での笑える話",
    "ピクニックの大失敗", "タクシー運転手の面白話", "配管工と客のジョーク",
    "初デートの失敗談集", "空港で荷物をなくした話", "バーベキューの失敗あるある",
    "自動車修理工場のコメディ", "コインランドリーの靴下ミステリー", "テント設営の悪夢",
    "セルフレジの苦悩", "待合室の雑誌あるある",
]

ja_jokes = [
    'ある男がバーに入って酒を注文した。バーテンダーが「どうしてそんなに浮かない顔をしているんだ？」と尋ねた。男は「妻が親友と浮気しているのを知ってしまったんだ」と答えた。バーテンダーは「それはひどい。どうするつもりだ？」と聞いた。男はため息をついて「まず妻に知っていると伝える。それから親友にも伝える」と言った。バーテンダーが「そのあとは？」と聞くと、男は「新しい親友と、できれば新しい妻を探す。誰か雇ってくれる人を知らないか？」と答えた。バーテンダーはダブルを注いで「その話なら、これはおごりだ」と言った。',
    '先生が「もし左手にリンゴが5個、右手に6個あったら、私は何を持っているでしょう？」と聞いた。ジョニーがすぐに手を挙げた。「はい、ジョニー？」ジョニーはニヤリとして「すごく大きな手です、先生！」と言った。教室中が大爆笑。先生はため息をついてもう一度挑戦した。「じゃあジョニー、君にウサギを2匹あげて、それから3匹追加であげたら、全部で何匹になる？」ジョニーは少し考えて「7匹です」と答えた。先生は嬉しそうに「正解！どうやってわかったの？」ジョニーは肩をすくめて「ウサギは1匹だけじゃ増えないからです。パパの給料明細を見て学びました」と言った。先生は次の科目に進むことにした。',
    '2人のプログラマーが深夜にデバッグしている。Aが「バグを見つけた！247行目のセミコロンが抜けてた！」と言った。Bは「ありえない、その行は10回チェックした」と答えた。Aは「まあ直したから、コミットして帰ろう」と言った。翌朝出社するとシステム全体がダウンしていた。4時間かけて調べた結果、Aがセミコロンを直すときに246行目に余計なセミコロンを追加していたことが判明。Bは画面を見つめて「バグ修正じゃなくて、バグ移行プログラムだったんだ」とつぶやいた。その日は誰も口をきかなかった。',
    '妻が夫に「私のこと可愛いと思う？それともブス？」と聞いた。夫はスマホから目を離さずに「両方だよ」と答えた。妻の目が細くなる。「両方ってどういう意味？」夫はやっと顔を上げて、自分がピンチだと気づいた。慌てて「つまり、君は可愛い…ブス…違う！言い間違えた！」と言葉を探す。「つまり、君があまりに可愛すぎて、他の女性が可哀想になるって意味で！」妻は腕を組んだ。「ナイスリカバリー。」夫は冷や汗を拭いた。「ありがとう、鏡の前で練習してたんだ。」妻はため息をついた。「明らかに練習不足ね。」',
    '面接官が「5年後の自分はどこにいると思いますか？」と聞いた。応募者は椅子にもたれて「理想的には、あなたの席に座って、人生がうまくいってるふりをしながら同じ質問をしていたいですね」と言った。面接官は無表情で見つめた。応募者は続けて「でも現実的には、経済が不安定なので、また同じ椅子に座って同じ仕事に応募しているでしょうね」と言った。面接官はノートを閉じた。「正直さは評価します。」応募者は「じゃあ採用？」と聞いた。面接官は「正直に言うと、ノーです。でもあなたのことは一生忘れません。」と答えた。',
]

while len(ja_jokes) < 50:
    base = random.choice(ja_jokes[:5])
    ja_jokes.append(base)

# ── Korean jokes (50) ────────────────────────────────────────────
ko_titles = [
    "웃음보장 직장인 유머 모음", "학교에서 있었던 레전드 에피소드", "부부의 일상 개그 베스트",
    "개발자만 이해할 수 있는 유머", "의사와 환자의 웃긴 대화", "선생님과 학생의 유쾌한 순간",
    "소개팅 대참사 모음집", "대중교통에서의 민망한 순간", "헬스장 실패담 컬렉션",
    "식당에서의 황당한 주문 썰", "아이들의 웃긴 말실수 베스트", "미용실에서 있었던 일",
    "공항에서의 여행 해프닝", "마트에서의 진상 손님 썰", "면접장 웃긴 답변 모음",
    "크리스마스 파티 대실패", "결혼식 축사 레전드", "이웃집 황당 스토리",
    "반려동물 집사 웃픈 이야기", "고객센터 신의 한수 응대", "캠핑 실패담 베스트",
    "아빠 육아 대참사 컬렉션", "룸메이트 지옥의 민족", "기술 실패 할머니도 이해함",
    "법정에서의 코미디 교환", "트레이너와 회원의 유머", "운전면허 시험 레전드",
    "엘리베이터 민망함 베스트", "고객 응대 레전드 답변", "명절 가족 싸움 개그",
    "형제자매 티격태격 코미디", "카페에서 엿들은 웃긴 대화", "도서관 조용한 혼란",
    "호텔 프런트 황당 썰", "영화관 꼬마 관객 썰", "생일파티 굴욕담",
    "화상통화 민망한 순간들", "온라인 쇼핑 리뷰 레전드", "치과에서 있었던 웃긴 일",
    "소풍 대참사 모음", "택시기사 황당 손님 썰", "배관공과 집주인 유머",
    "첫 데이트 대실패전", "공항 수하물 분실기", "바비큐 그릴 마스터 실패",
    "자동차 정비소 코미디", "빨래방 양말 미스터리", "텐트 설치의 악몽",
    "셀프 계산대의 고뇌", "대기실 잡지 컬렉션 유머",
]

ko_jokes = [
    '한 남자가 술집에 들어가서 술을 주문했다. 바텐더가 "왜 그렇게 긴 얼굴을 하고 있나요?"라고 물었다. 남자는 "아내가 내 절친과 바람피우고 있다는 걸 알게 됐어요"라고 대답했다. 바텐더가 "정말 안됐네요. 어떻게 할 건가요?"라고 묻자 남자는 한숨을 쉬며 "먼저 아내한테 내가 안다고 말할 거예요. 그리고 내 절친한테도 내가 안다고 말할 거예요"라고 했다. 바텐더가 "그 다음엔요?"라고 묻자 남자는 "그 다음엔 새 친구와 새 아내가 필요하겠죠. 누구 구인하는 사람 없나요?"라고 대답했다. 바텐더는 더블로 한 잔 따라주며 "그런 사연이면 이건 서비스입니다"라고 했다.',
    '선생님이 "만약 왼손에 사과 5개, 오른손에 6개가 있다면 저는 무엇을 가지고 있는 걸까요?"라고 물었다. 꼬마 조니가 바로 손을 들었다. "말해보세요, 조니." 조니는 씩 웃으며 "엄청 큰 손이요, 선생님!"이라고 말했다. 교실 전체가 웃음바다가 되었다. 선생님은 한숨을 쉬며 다시 시도했다. "자, 조니. 내가 너에게 토끼 2마리를 주고, 그 다음에 3마리를 더 준다면, 너는 토끼가 모두 몇 마리니?" 조니는 잠시 생각하더니 "7마리요"라고 대답했다. 선생님은 환하게 웃으며 "정답이야! 어떻게 알았니?" 조니는 어깨를 으쓱이며 "토끼는 한 마리만 줄 수가 없거든요. 계속 번식하니까요. 아빠 월급명세서에서 배웠어요"라고 말했다.',
    '두 프로그래머가 밤늦게 디버깅을 하고 있다. A가 "버그 찾았다! 247번째 줄에 세미콜론이 빠졌어!"라고 말했다. B는 "말도 안 돼, 그 줄은 내가 열 번이나 확인했어"라고 했다. A는 "어쨌든 고쳤으니 커밋하고 집에 가자"고 말했다. 그들은 코드를 커밋하고 퇴근했다. 다음 날 아침, 전체 시스템이 다운되었다. 4시간 동안 디버깅한 끝에 A가 세미콜론을 고치다가 실수로 246번째 줄에 세미콜론을 하나 더 추가했다는 것을 발견했다. B는 화면을 바라보며 "버그 수정이 아니라 버그 이전 프로그램이었어"라고 조용히 말했다. 그날 이후 아무도 말을 걸지 않았다.',
    '아내가 남편에게 물었다. "나 예뻐, 아니면 못생겼어?" 남편은 핸드폰에서 눈을 떼지 않고 "둘 다야"라고 말했다. 아내의 눈이 가늘어졌다. "둘 다라니 무슨 뜻이야?" 남편은 마침내 고개를 들었고 자신이 곤경에 빠졌다는 것을 깨달았다. 급히 "그러니까, 넌 예뻐... 아니 못생겼다는 게 아니라... 잠깐, 말이 잘못 나왔어!"라며 횡설수설했다. "내 말은 넌 너무 예뻐서 다른 여자들이 보면 가여울 정도라는 거야!" 아내는 팔짱을 꼈다. "말 돌리기 성공." 남편은 이마의 땀을 닦으며 "고마워, 거울 앞에서 연습했어"라고 했다. 아내는 한숨을 쉬며 "연습이 부족했네"라고 말했다.',
    '면접관이 "5년 후 자신의 모습은 어떨 것 같나요?"라고 물었다. 지원자는 의자에 기대어 "이상적으로는 당신 자리에 앉아서 인생이 잘 풀린 척하면서 똑같은 질문을 하고 싶네요"라고 말했다. 면접관이 멍하니 바라보자 지원자는 계속했다. "하지만 현실적으로는 경제가 불확실해서 아마 이 자리에서 이 직무에 다시 지원하고 있을 거예요." 면접관은 수첩을 덮으며 말했다. "솔직함은 높이 삽니다." 지원자가 "그럼 합격인가요?"라고 묻자 면접관은 대답했다. "솔직히 말하면, 아니에요. 하지만 당신을 영원히 기억할 거예요."',
]

while len(ko_jokes) < 50:
    base = random.choice(ko_jokes[:5])
    ko_jokes.append(base)

# ── Generate posts ───────────────────────────────────────────────
print('Generating 200 multilingual posts...')
posts = []

def make_posts(lang, titles, jokes, count):
    for i in range(count):
        base = random.choice(titles)
        suffix = f' #{i+1}'
        title = base + suffix
        if len(title) > 50:
            title = title[:47] + '...'
        while len(title) < 16:
            title = title + suffix

        joke_pool = random.sample(jokes, min(len(jokes), random.randint(1, 2)))
        content = '\n\n'.join(joke_pool)
        if len(content) > 1000:
            content = content[:997] + '...'
        elif len(content) < 200:
            extra = random.choice([j for j in jokes if j not in joke_pool])
            content = content + '\n\n' + extra
            if len(content) > 1000:
                content = content[:997] + '...'

        posts.append(Post(title=title, content=content, author=author))

make_posts('zh', zh_titles, zh_jokes, 50)
make_posts('en', en_titles, en_jokes, 50)
make_posts('ja', ja_titles, ja_jokes, 50)
make_posts('ko', ko_titles, ko_jokes, 50)

Post.objects.bulk_create(posts)
print(f'Created {Post.objects.count()} posts')

from django.db.models import Avg, Min, Max, Count
from django.db.models.functions import Length
s = Post.objects.aggregate(
    c=Count('id'),
    at=Avg(Length('title')), it=Min(Length('title')), xt=Max(Length('title')),
    ac=Avg(Length('content')), ic=Min(Length('content')), xc=Max(Length('content')),
)
print(f'Total:   {s["c"]}')
print(f'Title:   avg={s["at"]:.0f}  min={s["it"]}  max={s["xt"]}')
print(f'Content: avg={s["ac"]:.0f}  min={s["ic"]}  max={s["xc"]}')

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
samples = Post.objects.order_by('?')[:4]
for p in samples:
    ascii_c = sum(1 for c in p.content if ord(c) < 128)
    ratio = ascii_c / max(len(p.content), 1) * 100
    lang = 'EN' if ratio > 80 else ('ZH' if any('一' <= c <= '鿿' for c in p.content) else ('JA' if any('぀' <= c <= 'ヿ' for c in p.content) else 'KO'))
    print(f'  [{lang}] {p.title[:40]}... ({len(p.content)}c)')
