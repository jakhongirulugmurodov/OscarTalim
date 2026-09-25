// Statik ma'lumotlar: namuna so'zlar, mavzular, savollar, yutuqlar.
"use strict";

const CATEGORIES = [
  { id: "daily", name: "Daily Life", icon: "🏠" },
  { id: "school", name: "School", icon: "🎒" },
  { id: "work", name: "Work", icon: "💼" },
  { id: "travel", name: "Travel", icon: "✈️" },
  { id: "food", name: "Food", icon: "🍲" },
  { id: "tech", name: "Technology", icon: "💻" },
  { id: "health", name: "Health", icon: "🩺" },
  { id: "business", name: "Business", icon: "📈" },
];

const LEVELS = {
  beginner: { name: "Beginner", uz: "Boshlang'ich", dot: "🟢", n: 1 },
  intermediate: { name: "Intermediate", uz: "O'rta", dot: "🟡", n: 2 },
  advanced: { name: "Advanced", uz: "Yuqori", dot: "🔴", n: 3 },
};

const POS = ["noun", "verb", "adjective", "adverb", "phrase", "preposition", "conjunction", "pronoun", "idiom"];

// en | uz | pron | pos | level | cat | example
const SEED = `
improve|yaxshilamoq|/ɪmˈpruːv/|verb|intermediate|daily|I want to improve my English.
habit|odat|/ˈhæbɪt/|noun|beginner|daily|Reading every night is a good habit.
usually|odatda|/ˈjuːʒuəli/|adverb|beginner|daily|I usually wake up at seven.
tidy|tartibli, ozoda|/ˈtaɪdi/|adjective|beginner|daily|Please keep your room tidy.
borrow|qarzga olmoq|/ˈbɒrəʊ/|verb|intermediate|daily|Can I borrow your pen?
neighbor|qo'shni|/ˈneɪbər/|noun|beginner|daily|My neighbor has a big dog.
appointment|uchrashuv (belgilangan vaqt)|/əˈpɔɪntmənt/|noun|intermediate|daily|I have a doctor's appointment at five.
exhausted|juda charchagan|/ɪɡˈzɔːstɪd/|adjective|advanced|daily|She was exhausted after the long day.
beautiful|chiroyli|/ˈbjuːtɪfl/|adjective|beginner|daily|Tashkent is a beautiful city.
forget|unutmoq|/fəˈɡet/|verb|beginner|daily|Don't forget to call me tonight.
decide|qaror qilmoq|/dɪˈsaɪd/|verb|beginner|daily|I decided to learn English every day.
although|garchi|/ɔːlˈðəʊ/|conjunction|advanced|daily|Although it was raining, we went out.
homework|uy vazifasi|/ˈhəʊmwɜːk/|noun|beginner|school|I finish my homework before dinner.
explain|tushuntirmoq|/ɪkˈspleɪn/|verb|beginner|school|Can you explain this rule again?
knowledge|bilim|/ˈnɒlɪdʒ/|noun|intermediate|school|Books give us a lot of knowledge.
attend|qatnashmoq|/əˈtend/|verb|intermediate|school|All students must attend the meeting.
essay|insho|/ˈeseɪ/|noun|intermediate|school|I wrote an essay about my city.
curious|qiziquvchan|/ˈkjʊəriəs/|adjective|intermediate|school|Children are curious about everything.
memorize|yodlamoq|/ˈmeməraɪz/|verb|beginner|school|It is easy to memorize short words.
salary|maosh|/ˈsæləri/|noun|intermediate|work|Her salary is paid every month.
colleague|hamkasb|/ˈkɒliːɡ/|noun|intermediate|work|My colleague helped me with the report.
deadline|oxirgi muddat|/ˈdedlaɪn/|noun|intermediate|work|The deadline for this project is Friday.
experience|tajriba|/ɪkˈspɪəriəns/|noun|intermediate|work|He has five years of experience.
responsible|mas'uliyatli|/rɪˈspɒnsəbl/|adjective|advanced|work|She is responsible for the whole team.
achieve|erishmoq|/əˈtʃiːv/|verb|intermediate|work|You can achieve your goals with hard work.
journey|sayohat, yo'l|/ˈdʒɜːni/|noun|beginner|travel|The journey to Samarkand took four hours.
luggage|yuk (sayohat yuki)|/ˈlʌɡɪdʒ/|noun|intermediate|travel|My luggage is too heavy to carry.
abroad|chet elda|/əˈbrɔːd/|adverb|intermediate|travel|She wants to study abroad next year.
ticket|chipta|/ˈtɪkɪt/|noun|beginner|travel|I bought a train ticket online.
destination|manzil|/ˌdestɪˈneɪʃn/|noun|advanced|travel|Paris is a popular destination for tourists.
explore|kashf qilmoq, aylanib ko'rmoq|/ɪkˈsplɔː/|verb|intermediate|travel|We explored the old city on foot.
delicious|mazali|/dɪˈlɪʃəs/|adjective|beginner|food|This plov is really delicious.
recipe|retsept|/ˈresəpi/|noun|intermediate|food|My mother gave me her secret recipe.
hungry|och (qorni och)|/ˈhʌŋɡri/|adjective|beginner|food|I am hungry, so let's eat now.
ingredient|masalliq|/ɪnˈɡriːdiənt/|noun|advanced|food|Rice is the main ingredient of plov.
apple|olma|/ˈæpl/|noun|beginner|food|I eat an apple every day.
bitter|achchiq (ta'm)|/ˈbɪtə/|adjective|intermediate|food|This coffee tastes bitter.
device|qurilma|/dɪˈvaɪs/|noun|intermediate|tech|My phone is my favorite device.
download|yuklab olmoq|/ˌdaʊnˈləʊd/|verb|beginner|tech|You can download the app for free.
reliable|ishonchli|/rɪˈlaɪəbl/|adjective|advanced|tech|We need a reliable internet connection.
update|yangilamoq|/ʌpˈdeɪt/|verb|beginner|tech|Please update your computer tonight.
password|parol|/ˈpɑːswɜːd/|noun|beginner|tech|Never share your password with anyone.
invent|ixtiro qilmoq|/ɪnˈvent/|verb|intermediate|tech|Who invented the telephone?
healthy|sog'lom|/ˈhelθi/|adjective|beginner|health|Vegetables keep you healthy.
medicine|dori|/ˈmedsn/|noun|beginner|health|Take this medicine twice a day.
recover|tuzalmoq|/rɪˈkʌvə/|verb|intermediate|health|He recovered quickly after the flu.
exercise|jismoniy mashq|/ˈeksəsaɪz/|noun|beginner|health|I do exercise every morning.
symptom|alomat|/ˈsɪmptəm/|noun|advanced|health|Fever is a common symptom of flu.
prevent|oldini olmoq|/prɪˈvent/|verb|advanced|health|Washing your hands helps prevent illness.
customer|mijoz|/ˈkʌstəmə/|noun|beginner|business|The customer asked for a discount.
profit|foyda|/ˈprɒfɪt/|noun|intermediate|business|The company made a big profit this year.
negotiate|muzokara olib bormoq|/nɪˈɡəʊʃieɪt/|verb|advanced|business|We need to negotiate a better price.
invest|sarmoya kiritmoq|/ɪnˈvest/|verb|intermediate|business|He wants to invest in a small business.
meeting|yig'ilish|/ˈmiːtɪŋ/|noun|beginner|business|The meeting starts at ten o'clock.
efficient|samarali|/ɪˈfɪʃnt/|adjective|advanced|business|This new system is very efficient.
`.trim().split("\n").map(l => {
  const [en, uz, pron, pos, level, cat, ex] = l.split("|");
  return { en, uz, pron, pos, level, cat, ex };
});

// Suhbat mavzulari: savollar ketma-ketligi va mavzu so'zlari
const TOPICS = {
  daily: { name: "Daily life", icon: "☀️", uz: "Kundalik hayot",
    q: ["Hi! How was your day?", "What time do you usually wake up?", "What do you usually eat for breakfast?",
      "What did you do last weekend?", "What is your favorite way to relax?", "What are your plans for tomorrow?"],
    words: [["routine", "kun tartibi"], ["relax", "dam olmoq"], ["commute", "ishga qatnov"], ["chores", "uy yumushlari"], ["weekend", "dam olish kunlari"]] },
  shopping: { name: "Shopping", icon: "🛍️", uz: "Xarid",
    q: ["Hello! Can I help you find something today?", "What size do you need?", "Which color do you like more?",
      "This one costs forty dollars. Is that okay for you?", "Would you like to pay by card or cash?", "Do you often go shopping?"],
    words: [["discount", "chegirma"], ["receipt", "chek"], ["try on", "kiyib ko'rmoq"], ["refund", "pulni qaytarish"], ["cashier", "kassir"]] },
  restaurant: { name: "Restaurant", icon: "🍽️", uz: "Restoran",
    q: ["Good evening! Do you have a reservation?", "What would you like to drink?", "Are you ready to order?",
      "How would you like your steak cooked?", "How was your meal?", "Would you like some dessert?"],
    words: [["menu", "menyu"], ["order", "buyurtma bermoq"], ["bill", "hisob"], ["tip", "choychaqa"], ["reservation", "joy band qilish"]] },
  travel: { name: "Travel", icon: "✈️", uz: "Sayohat",
    q: ["Welcome to the airport! Where are you flying today?", "Is this your first time visiting this country?", "How long will you stay?",
      "Where are you going to stay?", "What places do you want to visit?", "What is the best trip you have ever had?"],
    words: [["passport", "pasport"], ["boarding pass", "samolyotga chiqish talon"], ["sightseeing", "diqqatga sazovor joylarni ko'rish"], ["accommodation", "turar joy"], ["delay", "kechikish"]] },
  interview: { name: "Job interview", icon: "💼", uz: "Ish suhbati",
    q: ["Good morning! Please tell me about yourself.", "Why do you want to work for our company?", "What are your strengths?",
      "Can you tell me about a difficult situation at work or school?", "Where do you see yourself in five years?", "Do you have any questions for us?"],
    words: [["strength", "kuchli tomon"], ["weakness", "zaif tomon"], ["qualification", "malaka"], ["hire", "ishga olmoq"], ["goal", "maqsad"]] },
  school: { name: "School", icon: "🎒", uz: "Maktab",
    q: ["Hi! What is your favorite subject?", "Why do you like it?", "What subject is difficult for you?",
      "How do you prepare for exams?", "Tell me about your best teacher.", "What do you want to study in the future?"],
    words: [["subject", "fan"], ["exam", "imtihon"], ["grade", "baho"], ["revise", "takrorlamoq"], ["classmate", "sinfdosh"]] },
  friends: { name: "Friends", icon: "🤝", uz: "Do'stlar",
    q: ["Hey! Tell me about your best friend.", "How did you meet?", "What do you usually do together?",
      "What makes a good friend?", "Did you do anything fun with friends recently?", "Do you prefer a few close friends or many friends?"],
    words: [["trust", "ishonch"], ["hang out", "birga vaqt o'tkazmoq"], ["support", "qo'llab-quvvatlamoq"], ["loyal", "sodiq"], ["argue", "bahslashmoq"]] },
  family: { name: "Family", icon: "👨‍👩‍👧", uz: "Oila",
    q: ["Hi! Tell me about your family.", "How many brothers and sisters do you have?", "Who are you most similar to in your family?",
      "What do you usually do together as a family?", "What is a family tradition you love?", "What did you learn from your parents?"],
    words: [["relative", "qarindosh"], ["tradition", "an'ana"], ["raise", "tarbiyalamoq"], ["similar", "o'xshash"], ["gathering", "yig'in"]] },
  business: { name: "Business", icon: "📈", uz: "Biznes",
    q: ["Good afternoon! Thanks for meeting me. What does your company do?", "Who are your main customers?", "What is your biggest challenge right now?",
      "How do you plan to grow next year?", "What price can you offer for a large order?", "When can we sign the contract?"],
    words: [["contract", "shartnoma"], ["revenue", "daromad"], ["partner", "hamkor"], ["growth", "o'sish"], ["offer", "taklif"]] },
};

const SIMPLE_QUESTIONS = [
  "What do you like to do on weekends?", "What is your favorite food and why?", "Describe your best friend.",
  "What did you do yesterday?", "What will you do tomorrow?", "Why are you learning English?",
  "What is the best place in your city?", "What is your dream job?", "Tell me about your favorite book or film.",
  "How do you usually spend your evenings?", "What is the weather like today?", "What makes you happy?",
];

const PICTURES = [
  { e: "🏖️☀️👨‍👩‍👧‍👦🍦", t: "A family day at the beach", hint: ["sunny", "swim", "ice cream", "relax"] },
  { e: "🏙️🚕🚦👩‍💼☔", t: "A busy city street in the rain", hint: ["traffic", "umbrella", "hurry", "office"] },
  { e: "🍳👨‍🍳🥕🧅🍲", t: "A man cooking dinner in the kitchen", hint: ["recipe", "ingredient", "delicious", "cook"] },
  { e: "📚👩‍🎓✏️🧑‍🏫🏫", t: "A lesson at school", hint: ["teacher", "explain", "homework", "student"] },
  { e: "✈️🧳🛂🌍🗺️", t: "Travelling abroad", hint: ["luggage", "passport", "journey", "explore"] },
  { e: "🏃‍♀️🌳🚴🐕🌤️", t: "People exercising in the park", hint: ["healthy", "exercise", "morning", "fresh air"] },
  { e: "💻☕📊👥🗓️", t: "A business meeting in an office", hint: ["meeting", "deadline", "colleague", "profit"] },
  { e: "🎂🎈🎁🥳👵", t: "A birthday party with the family", hint: ["celebrate", "gift", "guests", "happy"] },
];

const ROLEPLAYS = ["restaurant", "shopping", "travel", "interview"];

const ACHIEVEMENTS = [
  { id: "w10", icon: "🏆", name: "First 10 Words", uz: "10 ta so'z o'rganildi", test: s => s.learned >= 10 },
  { id: "w50", icon: "📗", name: "50 Words", uz: "50 ta so'z o'rganildi", test: s => s.learned >= 50 },
  { id: "w100", icon: "📚", name: "100 Words", uz: "100 ta so'z o'rganildi", test: s => s.learned >= 100 },
  { id: "m25", icon: "💎", name: "25 Mastered", uz: "25 ta so'z to'liq yodlandi", test: s => s.mastered >= 25 },
  { id: "s3", icon: "🔥", name: "3 Day Streak", uz: "3 kun ketma-ket", test: s => s.streak >= 3 },
  { id: "s7", icon: "🔥", name: "7 Day Streak", uz: "7 kun ketma-ket", test: s => s.streak >= 7 },
  { id: "s30", icon: "🌋", name: "30 Day Streak", uz: "30 kun ketma-ket", test: s => s.streak >= 30 },
  { id: "goal1", icon: "🎯", name: "Goal Getter", uz: "Birinchi kunlik maqsad bajarildi", test: s => s.goalsDone >= 1 },
  { id: "sp", icon: "🎤", name: "Speaking Master", uz: "20 ta gapirish mashqi, o'rtacha 70+", test: s => s.sp.n >= 20 && s.sp.avg >= 70 },
  { id: "wr", icon: "✍️", name: "Writing Master", uz: "50 ta yozish mashqi, 80%+", test: s => s.wr.t >= 50 && s.wr.pct >= 80 },
  { id: "li", icon: "🎧", name: "Listening Master", uz: "50 ta tinglash mashqi, 80%+", test: s => s.li.t >= 50 && s.li.pct >= 80 },
  { id: "vo", icon: "🧠", name: "Vocabulary Master", uz: "200 ta takrorlash, 85%+", test: s => s.vo.t >= 200 && s.vo.pct >= 85 },
  { id: "speed", icon: "⚡", name: "Lightning", uz: "Tezlik sinovida 20+ to'g'ri javob", test: s => s.bestSpeed >= 20 },
  { id: "talk", icon: "💬", name: "Chatterbox", uz: "5 ta suhbatni tugatdi", test: s => s.convos >= 5 },
  { id: "xp1k", icon: "⭐", name: "1000 XP", uz: "1000 XP to'pladi", test: s => s.xp >= 1000 },
  { id: "import", icon: "📥", name: "Collector", uz: "Ro'yxatdan so'zlarni import qildi", test: s => s.imported },
];

const DAILY_CHALLENGES = [
  { id: "speed15", t: "⚡ Tezlik sinovida 15 ta to'g'ri javob", xp: 40 },
  { id: "speak3", t: "🎤 Uchta so'zni gapirib gapda ishlating", xp: 40 },
  { id: "convo", t: "💬 Bitta suhbatni oxirigacha olib boring", xp: 50 },
  { id: "match", t: "🧩 Juftlash o'yinini xatosiz tugating", xp: 40 },
  { id: "dict5", t: "🎧 5 ta diktantni to'g'ri yozing", xp: 40 },
  { id: "sent3", t: "✍️ 3 ta o'z gapingizni yozing (80+ ball)", xp: 40 },
  { id: "memory", t: "🃏 Xotira o'yinini 20 urinishdan kam tugating", xp: 40 },
];

const LEVEL_NAMES = ["Starter", "Explorer", "Learner", "Speaker", "Writer", "Achiever", "Expert", "Master", "Champion", "Legend"];
