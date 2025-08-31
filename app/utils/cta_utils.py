def detect_category(text: str) -> str:
    t=text.lower()
    if any(k in t for k in ["flood","earthquake","cyclone","disaster","crash"]): return "disaster"
    if any(k in t for k in ["breaking","urgent","just in","developing"]): return "breaking"
    if any(k in t for k in ["rupee","inflation","budget","economy","gdp","stock","sensex"]): return "economy"
    if any(k in t for k in ["ipl","cricket","world cup","t20","odi","bcci"]): return "cricket"
    if any(k in t for k in ["ai ","tech","startup","google","apple","meta","openai"]): return "tech"
    if any(k in t for k in ["election","minister","bjp","congress","parliament","vote"]): return "politics"
    return "default"

def generate_cta(category: str, title: str) -> str:
    options={
      "tech":["🤖 Game changer or hype?","🚀 Excited or worried?"],
      "economy":["📊 What's your take?","💰 Share your thoughts"],
      "cricket":["🏏 Who’s your MOTM?","🎯 Your prediction?"],
      "politics":["🗳️ Agree or disagree?","📊 Good move or not?"],
      "disaster":["🙏 Stay safe everyone","❤️ Thoughts and prayers"],
      "breaking":["⚡ Your instant reaction?","🔥 What's your view?"],
      "default":["💭 What's your POV?","🎯 Share your thoughts"]
    }
    import hashlib
    arr=options.get(category,options["default"])
    seed=int(hashlib.md5(title.encode()).hexdigest()[:8],16)
    return arr[seed%len(arr)]