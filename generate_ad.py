#!/usr/bin/env python3
"""
Hotel Riviera — Cinematic 60s Ad Generator
Produces a single self-contained HTML file with all images embedded
as optimised base64 JPEGs. No external assets required.
"""

import base64, io, os, sys, json
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance

# ─── PATHS ───────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).parent
IMG    = ROOT / 'img'
OUT    = ROOT / 'hotel-riviera-final.html'

# ─── IMAGE PROCESSING ────────────────────────────────────────────────────────

def load(fname, max_w=1600, quality=84, sharpen=False):
    """Load, resize, optionally sharpen, and return as base64 data-URI."""
    path = IMG / fname
    if not path.exists():
        print(f"  [!] missing: {fname}", file=sys.stderr)
        return ""
    img = Image.open(path).convert("RGB")
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    if sharpen:
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=3))
    # Slight contrast boost for cinematic look
    img = ImageEnhance.Contrast(img).enhance(1.08)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    orig_kb = path.stat().st_size // 1024
    new_kb  = len(buf.getvalue()) // 1024
    print(f"  {fname:30s} {orig_kb:>5}KB → {new_kb:>4}KB", file=sys.stderr)
    return f"data:image/jpeg;base64,{b64}"

def load_png(fname, max_w=800):
    """Load PNG (lace/logo) keeping transparency, return as base64 PNG."""
    path = IMG / fname
    if not path.exists():
        return ""
    img = Image.open(path)
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"

# ─── SCENE MANIFEST ──────────────────────────────────────────────────────────
# Each dict drives both CSS/HTML generation and GSAP timing.
# t_in  = timeline second when scene becomes visible
# t_out = timeline second when scene disappears
# t_rev = timeline second when inner reveals start

SCENES = [
    dict(id="s1", t_in=0,    t_out=8,    t_rev=1.0,  type="logo"),
    dict(id="s2", t_in=8,    t_out=18,   t_rev=8.35, type="photo",
         bg="exterior2.jpg",  overlay="left",
         tag="OPPLEV",  h1="Moss",       h2="ved sjøen",  sub="50 MINUTTER FRA OSLO",
         waves=True),
    dict(id="s3", t_in=18,   t_out=28,   t_rev=18.35, type="rooms",
         tag="OVERNATTING",
         rooms=[("Riviera Stay","fra 1 145 kr"),("Superior Ocean View","fra 1 220 kr"),
                ("Ocean Front Premium","fra 1 545 kr"),("Ocean Front Suite","fra 2 545 kr")]),
    dict(id="s4", t_in=28,   t_out=38,   t_rev=28.4,  type="photo",
         bg="spa.png",        overlay="bottom",
         tag="AVSLAPNING",    h1="Pool &amp;", h2="Wellness",
         sub="Spa · Basseng · Behandlinger · Dag Spa Pakker",
         layout="bottom", lace_top=True),
    dict(id="s5", t_in=38,   t_out=48,   t_rev=38.4,  type="photo",
         bg="brasserie.png",  overlay="bottom",
         tag="RESTAURANTEN",  h1="Brasserie",  h2="Bon Vivant",
         sub="Lunsj · Middag · Pizza · Bar",
         layout="bottom", lace_top=True, italic=True),
    dict(id="s6", t_in=48,   t_out=58,   t_rev=48.4,  type="offer",
         bg="terrasse.jpg",   overlay="dark",
         tag="SPESIALTILBUD", h1="Riviera",    h2="Sundays",
         price="fra 1 795 kr for 2 personer",
         sub="— 30 % Early Bird Rabatt på sommer —",
         lace_top=True, lace_bot=True),
    dict(id="s7", t_in=58,   t_out=70,   t_rev=58.85, type="outro",
         bg="main-hotel.jpg",
         quote="«It’s not just a place – it’s a feeling»",
         lace_top=True, lace_bot=True),
]

LOOP = 70  # total seconds

# ─── CSS KEYFRAME HELPERS ────────────────────────────────────────────────────

def pct(s):
    return f"{s / LOOP * 100:.3f}%"

def scene_keyframes():
    lines = []
    # scene 1: fade in from t=0
    s = SCENES[0]
    fade = 1.0
    lines.append(f"""#s1{{animation:A1 {LOOP}s linear infinite}}
@keyframes A1{{0%{{opacity:0}}{pct(fade)}{{opacity:1}}{pct(s['t_out']-1)}{{opacity:1}}{pct(s['t_out'])}{{opacity:0}}100%{{opacity:0}}}}""")
    for i, s in enumerate(SCENES[1:], 2):
        prev = SCENES[i-2]
        fade = 1.0
        lines.append(f"""#{s['id']}{{animation:A{i} {LOOP}s linear infinite}}
@keyframes A{i}{{0%{{opacity:0}}{pct(prev['t_out']-1)}{{opacity:0}}{pct(prev['t_out'])}{{opacity:1}}{pct(s['t_out']-1)}{{opacity:1}}{pct(s['t_out'])}{{opacity:0}}100%{{opacity:0}}}}""")
    return "\n".join(lines)

# ─── HTML BUILDERS ───────────────────────────────────────────────────────────

def scene_html(s, imgs):
    sid = s['id']
    typ = s['type']

    def bg_div():
        src = imgs.get(s.get('bg',''), '')
        pos = s.get('bg_pos', 'center center')
        return f'<div class="bg" id="bg_{sid}" style="background-image:url(\'{src}\');background-position:{pos}"></div>' if src else ''

    def overlays():
        ov = s.get('overlay', '')
        if ov == 'left':
            return '<div class="ov-l"></div>'
        if ov == 'bottom':
            return '<div class="ov-b"></div>'
        if ov == 'dark':
            return '<div class="ov-dk" style="background:rgba(42,15,28,.85)"></div>'
        return ''

    def laces():
        t = '<div class="lt"></div>' if s.get('lace_top') else ''
        b = '<div class="lb"></div>' if s.get('lace_bot') else ''
        return t + b

    if typ == 'logo':
        return f'''<div class="scene" id="{sid}" style="background:radial-gradient(ellipse at center,#3D1A2A 0%,#2A0F1C 100%)">
  <div class="lt"></div><div class="lb"></div>
  <div class="cnt cc">
    {_fan_svg('fan1')}
    <div id="logoico" style="margin-bottom:.8em">{_logo_svg(large=True, imgs=imgs)}</div>
    <div>
      <div class="lm"><div id="lhtl" class="lhtl">HOTEL</div></div>
      <div id="lnm" class="lnm">Riviera</div>
      <div id="lrl" class="rl" style="width:0;margin:1.1em auto"></div>
      <div class="lm" style="margin-top:.4em"><div id="lsub" class="lsub">Moss · Norge</div></div>
    </div>
    {_fan_svg('fan2', flip=True)}
  </div>
</div>'''

    if typ == 'photo':
        layout = s.get('layout', 'center')
        cnt_cls = 'cc' if layout == 'center' else 'cb' if layout == 'bottom' else ''
        italic  = s.get('italic', False)
        ht_cls  = 'it' if italic else 'xl'
        waves   = _waves_html() if s.get('waves') else ''
        return f'''<div class="scene" id="{sid}">
  {bg_div()}{overlays()}{laces()}{waves}
  <div class="cnt {cnt_cls}">
    <div class="lm"><div id="{sid}t" class="tag">{s['tag']}</div></div>
    <div class="lm"><div id="{sid}h1" class="{ht_cls}">{s['h1']}</div></div>
    <div class="lm"><div id="{sid}h2" class="{ht_cls}" style="color:var(--pink)">{s['h2']}</div></div>
    <div id="{sid}rl" class="rl" style="width:0;margin:1.6em 0"></div>
    <div id="{sid}sm" class="sm">{s['sub']}</div>
  </div>
</div>'''

    if typ == 'rooms':
        room_imgs = ['room-a.jpg','room-b.jpg','room-c.jpg','room-d.jpg']
        ri_html = ''.join(f'<div class="ri" style="background-image:url(\'{imgs.get(r,"")}\')" ></div>' for r in room_imgs)
        rows_html = ''.join(
            f'<div id="{sid}r{i+1}" class="rrow"><span class="rn">{name}</span><span class="rp">{price}</span></div>'
            for i,(name,price) in enumerate(s['rooms'])
        )
        return f'''<div class="scene" id="{sid}" style="background:var(--dark)">
  <div class="bg" style="background-image:url(\'{imgs.get("hotel-view.jpg","")}'\');opacity:.15;filter:blur(3px)"></div>
  <div class="rmosaic">{ri_html}</div>
  <div class="rfade"></div>
  <div class="lb"></div>
  <div class="rtxt">
    <div class="lm"><div id="{sid}t" class="tag">{s['tag']}</div></div>
    <div class="lm"><div id="{sid}h" class="lg">Velg din<br><em>utsikt</em></div></div>
    {rows_html}
  </div>
</div>'''

    if typ == 'offer':
        return f'''<div class="scene" id="{sid}">
  {bg_div()}{overlays()}{laces()}
  <div class="cnt">
    <div class="lm"><div id="{sid}t" class="tag">{s['tag']}</div></div>
    <div class="lm"><div id="{sid}h1" class="xl">{s['h1']}</div></div>
    <div class="lm"><div id="{sid}h2" class="xl">{s['h2']}</div></div>
    <div class="lm"><div id="{sid}pr" class="it" style="color:var(--rose);font-size:clamp(15px,2.5vw,34px)">{s['price']}</div></div>
    <div id="{sid}sm" class="sm">{s['sub']}</div>
    <div id="{sid}btn" class="btn">BOOK PÅ HOTELRIVIERA.NO</div>
  </div>
</div>'''

    if typ == 'outro':
        src = imgs.get(s.get('bg',''), '')
        return f'''<div class="scene" id="{sid}">
  <div class="bg" id="bg_{sid}" style="background-image:url(\'{src}\')"></div>
  <div class="ov-dk" style="background:rgba(42,15,28,.76)"></div>
  {laces()}
  <div class="cnt cc">
    <div id="{sid}q" style="font-style:italic;font-size:clamp(13px,2.1vw,30px);max-width:68vw;line-height:1.7;margin-bottom:2em;color:var(--pink)">{s['quote']}</div>
    <div id="{sid}ico" style="display:flex;justify-content:center;margin-bottom:.7em">{_logo_svg(large=False, imgs=imgs)}</div>
    <div class="lm"><div id="{sid}oh" class="oh">HOTEL</div></div>
    <div class="lm"><div id="{sid}on" class="on">Riviera</div></div>
    <div id="{sid}rl" class="rl" style="width:0;margin:1.1em auto"></div>
    <div id="{sid}ou" class="ou">hotelriviera.no</div>
  </div>
</div>'''

    return ''

def _fan_svg(id_, flip=False):
    flip_style = 'transform:scaleY(-1);' if flip else ''
    return f'''<svg id="{id_}" viewBox="0 0 200 42" xmlns="http://www.w3.org/2000/svg"
     style="width:clamp(80px,14vw,180px);margin:{'top' if flip else 'bottom'}:.4em;{flip_style}">
  <g stroke="#C4889A" stroke-width=".6" fill="none" opacity=".72">
    <path d="M100,40 A38,38 0 0,1 62,40"/><path d="M100,40 A38,38 0 0,0 138,40"/>
    <path d="M100,40 A26,26 0 0,1 74,40"/><path d="M100,40 A26,26 0 0,0 126,40"/>
    <path d="M100,40 A15,15 0 0,1 85,40"/><path d="M100,40 A15,15 0 0,0 115,40"/>
    <path d="M100,40 A6,6 0 0,1 94,40"/> <path d="M100,40 A6,6 0 0,0 106,40"/>
    <line x1="100" y1="40" x2="62" y2="2"/>
    <line x1="100" y1="40" x2="74" y2="0"/>
    <line x1="100" y1="40" x2="86" y2="0"/>
    <line x1="100" y1="40" x2="100" y2="0"/>
    <line x1="100" y1="40" x2="114" y2="0"/>
    <line x1="100" y1="40" x2="126" y2="0"/>
    <line x1="100" y1="40" x2="138" y2="2"/>
    <line x1="54" y1="40" x2="146" y2="40" stroke-width=".9"/>
  </g>
</svg>'''

def _logo_svg(large=True, imgs=None):
    w = "clamp(85px,12vw,140px)" if large else "clamp(48px,6vw,76px)"
    return f'''<svg viewBox="0 0 130 130" xmlns="http://www.w3.org/2000/svg"
     style="width:{w};filter:drop-shadow(0 5px 22px rgba(0,0,0,.55))">
  <circle cx="65" cy="65" r="62" fill="#F0C4C4"/>
  <circle cx="65" cy="65" r="59" fill="none" stroke="#3D1A2A" stroke-width=".9" opacity=".32"/>
  <circle cx="65" cy="65" r="55" fill="none" stroke="#3D1A2A" stroke-width=".4" opacity=".16"/>
  <!-- trunk -->
  <path d="M65,96 C63,87 62,78 63,69 C64,60 65,54 65,48" stroke="#3D1A2A" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M67,96 C65.5,87 65,79 65.5,71" stroke="#3D1A2A" stroke-width="1.1" fill="none" stroke-linecap="round" opacity=".22"/>
  <!-- left fronds -->
  <path d="M64,52 C52,44 40,41 33,46"  stroke="#3D1A2A" stroke-width="2.2" fill="none" stroke-linecap="round"/>
  <path d="M64,54 C53,48 46,45 41,49"  stroke="#3D1A2A" stroke-width="1.0" fill="none" stroke-linecap="round" opacity=".36"/>
  <path d="M64,57 C55,53 49,50 44,54"  stroke="#3D1A2A" stroke-width="1.6" fill="none" stroke-linecap="round"/>
  <!-- right fronds -->
  <path d="M66,52 C78,44 90,41 97,46"  stroke="#3D1A2A" stroke-width="2.2" fill="none" stroke-linecap="round"/>
  <path d="M66,54 C77,48 84,45 89,49"  stroke="#3D1A2A" stroke-width="1.0" fill="none" stroke-linecap="round" opacity=".36"/>
  <path d="M66,57 C75,53 81,50 86,54"  stroke="#3D1A2A" stroke-width="1.6" fill="none" stroke-linecap="round"/>
  <!-- center fronds -->
  <path d="M65,48 C62,38 60,30 62,23"  stroke="#3D1A2A" stroke-width="2.0" fill="none" stroke-linecap="round"/>
  <path d="M65,49 C68,39 70,31 68,23"  stroke="#3D1A2A" stroke-width="1.3" fill="none" stroke-linecap="round"/>
  <path d="M65,50 C57,41 52,36 48,33"  stroke="#3D1A2A" stroke-width="1.3" fill="none" stroke-linecap="round"/>
  <path d="M65,50 C73,41 78,36 82,33"  stroke="#3D1A2A" stroke-width="1.3" fill="none" stroke-linecap="round"/>
  <!-- labels -->
  <text x="65" y="21"  font-family="Arial,sans-serif" font-size="7.5" font-weight="500"
        fill="#3D1A2A" text-anchor="middle" letter-spacing="3.5">HOTEL</text>
  <text x="65" y="111" font-family="Georgia,serif" font-size="13" font-weight="bold"
        fill="#3D1A2A" text-anchor="middle" letter-spacing="2.5">RIVIERA</text>
  <line x1="30" y1="115" x2="100" y2="115" stroke="#3D1A2A" stroke-width=".65" opacity=".28"/>
  <circle cx="65" cy="119" r="1.1" fill="#3D1A2A" opacity=".28"/>
</svg>'''

def _waves_html():
    return '''<div class="wvs">
  <div class="wv wv1"><svg viewBox="0 0 1440 200" preserveAspectRatio="none" width="100%" height="100%">
    <path d="M0,100 C360,180 720,20 1080,100 C1260,140 1350,60 1440,100 L1440,200 L0,200Z" fill="rgba(42,15,28,.52)"/>
  </svg></div>
  <div class="wv wv2"><svg viewBox="0 0 1440 200" preserveAspectRatio="none" width="100%" height="100%">
    <path d="M0,80 C300,160 600,20 900,80 C1050,110 1200,40 1440,80 L1440,200 L0,200Z" fill="rgba(42,15,28,.36)"/>
  </svg></div>
</div>'''

# ─── GSAP TIMELINE BUILDER ───────────────────────────────────────────────────

def gsap_js(imgs):
    lace = imgs.get('lace', '')

    # Compute wipe times (midpoint between consecutive scenes)
    wipes = []
    for i in range(len(SCENES)-1):
        mid = (SCENES[i]['t_out'] + SCENES[i+1]['t_in']) / 2
        wipes.append(f"wipe({mid:.1f});")
    wipes_str = "  ".join(wipes)

    # Ken Burns entries
    kb_lines = []
    kb_configs = [
        ("bg_s2", 8,  "{{scale:1.12,xPercent:0}}", "{{scale:1.0,xPercent:-1.5,duration:11,ease:'none'}}"),
        ("bg_s4", 28, "{{scale:1.0,xPercent:1}}",  "{{scale:1.10,xPercent:-1,duration:11,ease:'none'}}"),
        ("bg_s5", 38, "{{scale:1.10,xPercent:0}}", "{{scale:1.0,xPercent:1.5,duration:11,ease:'none'}}"),
        ("bg_s6", 48, "{{scale:1.0,xPercent:-1}}", "{{scale:1.10,xPercent:1,duration:11,ease:'none'}}"),
        ("bg_s7", 58, "{{scale:1.08,xPercent:0}}", "{{scale:1.0,xPercent:-1,duration:12,ease:'none'}}"),
    ]
    for (bid, t, frm, to) in kb_configs:
        kb_lines.append(f"tl.fromTo('#{bid}',{frm},{to},{t});")
    kb_str = "\n  ".join(kb_lines)

    return f'''/* ═══════════════════════════════════════
   Generated by generate_ad.py
   GSAP 70s master timeline — CSS keyframes
   control scene opacity; GSAP drives all
   inner reveals, Ken Burns, curtain wipes.
═══════════════════════════════════════ */
var tl = gsap.timeline({{ repeat: -1 }});

/* ── CURTAIN WIPE — burgundy panel L→R ── */
function wipe(t) {{
  tl.fromTo('#curt',
    {{clipPath:'inset(0 100% 0 0)'}},
    {{clipPath:'inset(0 0% 0 0)',duration:.28,ease:'power2.in'}}, t
  ).to('#curt',{{clipPath:'inset(0 0 0 100%)',duration:.28,ease:'power2.out'}}, t+.28);
}}
{wipes_str}

/* ── INITIAL HIDDEN STATES ── */
gsap.set(['#fan1','#fan2','#logoico','#lnm'], {{opacity:0}});
gsap.set(['#lhtl','#lsub'],  {{yPercent:115}});
gsap.set('#lrl', {{width:0}});
// all scene inner elements start hidden
var _yp = '#s2t,#s2h1,#s2h2,#s3t,#s3h,#s4t,#s4h1,#s4h2,#s5t,#s5h1,#s5h2,#s6t,#s6h1,#s6h2,#s6pr,#s7oh,#s7on';
gsap.set(_yp, {{yPercent:115}});
gsap.set('#s2rl,#s4rl,#s5rl,#s6rl,#s7rl', {{width:0}});
gsap.set('#s2sm,#s4sm,#s5sm,#s6sm,#s6btn,#s7q,#s7ico,#s7ou', {{opacity:0}});
gsap.set('#s3r1,#s3r2,#s3r3,#s3r4', {{opacity:0,x:-30}});

/* ── KEN BURNS ── */
{kb_str}

/* ── SCRAMBLE "Riviera" ── */
tl.set('#lnm',{{opacity:0}},0);
tl.call(function(){{
  var T='Riviera',C='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
  var el=document.getElementById('lnm');
  gsap.set(el,{{opacity:1}});
  var s=null;
  requestAnimationFrame(function f(ts){{
    if(!s)s=ts;
    var p=Math.min((ts-s)/1900,1);
    var ok=Math.floor(p*T.length*1.5),out='';
    for(var i=0;i<T.length;i++) out+=(i<ok)?T[i]:C[Math.floor(Math.random()*C.length)];
    el.textContent=out;
    if(p<1)requestAnimationFrame(f); else el.textContent=T;
  }});
}},null,1.9);

/* ── S1 LOGO REVEAL (0–8s) ── */
tl.to('#fan1',{{opacity:1,duration:.7,ease:'power2.out'}},1.0);
tl.fromTo('#logoico',{{opacity:0,scale:.86,y:18}},{{opacity:1,scale:1,y:0,duration:1.5,ease:'expo.out'}},1.35);
tl.to('#lhtl',{{yPercent:0,duration:.75,ease:'expo.out'}},1.72);
tl.to('#fan2',{{opacity:1,duration:.7,ease:'power2.out'}},2.2);
tl.to('#lrl',{{width:88,duration:1.3,ease:'expo.out'}},2.85);
tl.to('#lsub',{{yPercent:0,duration:.8,ease:'expo.out'}},3.35);

/* ── S2 ATMOSFÆRE (8–18s) ── */
tl.set('#s2t,#s2h1,#s2h2',{{yPercent:115}},7.8);
tl.set('#s2rl',{{width:0}},7.8);
tl.set('#s2sm',{{opacity:0,y:14}},7.8);
tl.to('#s2t', {{yPercent:0,duration:.65,ease:'expo.out'}},8.35);
tl.to('#s2h1',{{yPercent:0,duration:1.05,ease:'expo.out'}},8.65);
tl.to('#s2h2',{{yPercent:0,duration:.95,ease:'expo.out'}},9.25);
tl.to('#s2rl',{{width:44,duration:1.1,ease:'expo.out'}},9.95);
tl.to('#s2sm',{{opacity:1,y:0,duration:.9,ease:'expo.out'}},10.45);

/* ── S3 ROM (18–28s) ── */
tl.set('#s3t,#s3h',{{yPercent:115}},17.3);
tl.set('#s3r1,#s3r2,#s3r3,#s3r4',{{opacity:0,x:-30}},17.3);
tl.to('#s3t',{{yPercent:0,duration:.65,ease:'expo.out'}},18.35);
tl.to('#s3h',{{yPercent:0,duration:1.05,ease:'expo.out'}},18.65);
tl.to('#s3r1,#s3r2,#s3r3,#s3r4',{{opacity:1,x:0,stagger:.28,duration:.65,ease:'expo.out'}},19.4);

/* ── S4 WELLNESS (28–38s) ── */
tl.set('#s4t,#s4h1,#s4h2',{{yPercent:115}},27.5);
tl.set('#s4rl',{{width:0}},27.5);
tl.set('#s4sm',{{opacity:0,y:14}},27.5);
tl.to('#s4t', {{yPercent:0,duration:.65,ease:'expo.out'}},28.4);
tl.to('#s4h1',{{yPercent:0,duration:1.05,ease:'expo.out'}},28.72);
tl.to('#s4h2',{{yPercent:0,duration:1.05,ease:'expo.out'}},29.18);
tl.to('#s4sm',{{opacity:1,y:0,duration:.9,ease:'expo.out'}},29.85);
tl.to('#s4rl',{{width:44,duration:1.1,ease:'expo.out'}},30.35);

/* ── S5 RESTAURANT (38–48s) ── */
tl.set('#s5t,#s5h1,#s5h2',{{yPercent:115}},37.7);
tl.set('#s5rl',{{width:0}},37.7);
tl.set('#s5sm',{{opacity:0,y:14}},37.7);
tl.to('#s5t', {{yPercent:0,duration:.65,ease:'expo.out'}},38.4);
tl.to('#s5h1',{{yPercent:0,duration:1.1,ease:'expo.out'}},38.72);
tl.to('#s5h2',{{yPercent:0,duration:1.1,ease:'expo.out'}},39.22);
tl.to('#s5rl',{{width:44,duration:1.1,ease:'expo.out'}},39.88);
tl.to('#s5sm',{{opacity:1,y:0,duration:.9,ease:'expo.out'}},40.38);

/* ── S6 TILBUD (48–58s) ── */
tl.set('#s6t,#s6h1,#s6h2,#s6pr',{{yPercent:115}},47.9);
tl.set('#s6sm,#s6btn',{{opacity:0}},47.9);
tl.set('#s6rl',{{width:0}},47.9);
tl.to('#s6t', {{yPercent:0,duration:.65,ease:'expo.out'}},48.4);
tl.to('#s6h1',{{yPercent:0,duration:1.1,ease:'expo.out'}},48.72);
tl.to('#s6h2',{{yPercent:0,duration:1.1,ease:'expo.out'}},49.18);
tl.to('#s6pr',{{yPercent:0,duration:.95,ease:'expo.out'}},49.78);
tl.to('#s6sm',{{opacity:1,duration:.85,ease:'power2.out'}},50.28);
tl.fromTo('#s6btn',{{opacity:0,scale:.88}},{{opacity:1,scale:1,duration:.9,ease:'back.out(1.4)'}},50.88);

/* ── S7 OUTRO (58–70s) ── */
tl.set('#s7oh,#s7on',{{yPercent:115}},58.0);
tl.set('#s7rl',{{width:0}},58.0);
tl.set('#s7q,#s7ico,#s7ou',{{opacity:0}},58.0);
tl.fromTo('#s7q', {{opacity:0,y:12}},{{opacity:1,y:0,duration:1.9,ease:'power2.out'}},58.88);
tl.fromTo('#s7ico',{{opacity:0,scale:.88,y:15}},{{opacity:1,scale:1,y:0,duration:1.4,ease:'expo.out'}},60.88);
tl.to('#s7oh',{{yPercent:0,duration:.8,ease:'expo.out'}},61.28);
tl.to('#s7on',{{yPercent:0,duration:1.1,ease:'expo.out'}},61.68);
tl.to('#s7rl',{{width:88,duration:1.4,ease:'expo.out'}},62.48);
tl.to('#s7ou',{{opacity:1,duration:.9,ease:'power2.out'}},63.1);

/* ── RESET S1 for next loop ── */
tl.set(['#fan1','#fan2','#logoico'],{{opacity:0}},69.4);
tl.set(['#lhtl','#lsub'],{{yPercent:115}},69.4);
tl.set('#lrl',{{width:0}},69.4);

/* ── GLOWING PARTICLES ── */
(function(){{
  var cv=document.getElementById('pcv'),cx=cv.getContext('2d');
  function rs(){{cv.width=innerWidth;cv.height=innerHeight;}}
  rs();window.addEventListener('resize',rs);
  var COLS=[[240,196,196],[196,136,154],[253,245,240],[212,149,154],[224,168,176],[230,188,194]];
  var P=Array.from({{length:95}},function(_,i){{
    var c=COLS[i%COLS.length];
    return {{x:Math.random()*innerWidth,y:Math.random()*innerHeight,
      r:Math.random()*1.9+.2,vy:Math.random()*.25+.04,
      vx:(Math.random()-.5)*.16,op:Math.random()*.42+.04,
      dop:(Math.random()-.5)*.005,col:c,glow:i%4===0}};
  }});
  (function draw(){{
    cx.clearRect(0,0,cv.width,cv.height);
    P.forEach(function(p){{
      p.y-=p.vy;p.x+=p.vx;p.op+=p.dop;
      if(p.op>.46){{p.op=.46;p.dop*=-1;}}
      if(p.op<.02){{p.op=.02;p.dop*=-1;}}
      if(p.y<-6){{p.y=cv.height+6;p.x=Math.random()*cv.width;}}
      if(p.x<-6)p.x=cv.width+6;
      if(p.x>cv.width+6)p.x=-6;
      cx.save();
      if(p.glow){{cx.shadowBlur=9;cx.shadowColor='rgba('+p.col+',.5)';}}
      cx.beginPath();cx.arc(p.x,p.y,p.r,0,6.2832);
      cx.fillStyle='rgba('+p.col+','+p.op.toFixed(3)+')';
      cx.fill();cx.restore();
    }});
    requestAnimationFrame(draw);
  }})();
}})();'''

# ─── MAIN HTML ASSEMBLY ──────────────────────────────────────────────────────

def build():
    print("\n🏨 Hotel Riviera Ad Generator", file=sys.stderr)
    print("─" * 40, file=sys.stderr)

    print("\nOptimising images...", file=sys.stderr)
    imgs = {
        'exterior2.jpg':  load('exterior2.jpg',  max_w=1600, quality=85, sharpen=True),
        'room-a.jpg':     load('room-a.jpg',      max_w=900,  quality=82),
        'room-b.jpg':     load('room-b.jpg',      max_w=900,  quality=82),
        'room-c.jpg':     load('room-c.jpg',      max_w=900,  quality=82),
        'room-d.jpg':     load('room-d.jpg',      max_w=900,  quality=82),
        'spa.png':        load('spa.png',          max_w=1200, quality=84, sharpen=True),
        'brasserie.png':  load('brasserie.png',    max_w=1200, quality=84),
        'terrasse.jpg':   load('terrasse.jpg',     max_w=1200, quality=84),
        'main-hotel.jpg': load('main-hotel.jpg',   max_w=1400, quality=85),
        'hotel-view.jpg': load('hotel-view.jpg',   max_w=1000, quality=80),
        'lace':           load_png('lace-official.png', max_w=600),
    }
    lace_src = imgs['lace']

    print("\nBuilding HTML...", file=sys.stderr)

    scenes_html = "\n\n".join(scene_html(s, imgs) for s in SCENES)
    css_kf      = scene_keyframes()
    js          = gsap_js(imgs)

    html = f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hotel Riviera — 60s Ad</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Montserrat:wght@200;300;400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<style>
/* ═══════════════════════════════════════════
   Hotel Riviera · Brand Palette
   Pink   #F0C4C4  Burgundy #3D1A2A
   Rose   #C4889A  Dark     #2A0F1C  Cream #FDF5F0
═══════════════════════════════════════════ */
:root{{--pink:#F0C4C4;--rose:#C4889A;--burg:#3D1A2A;--dark:#2A0F1C;--cream:#FDF5F0}}
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:100%;height:100%;background:var(--dark);overflow:hidden;
  font-family:'Cormorant Garamond',Georgia,serif}}
body::before,body::after{{content:'';position:fixed;left:0;right:0;
  height:clamp(14px,3.8vh,46px);background:#000;z-index:55;pointer-events:none}}
body::before{{top:0}}body::after{{bottom:0}}
#vig{{position:fixed;inset:0;z-index:46;pointer-events:none;
  background:radial-gradient(ellipse 80% 80% at 50% 50%,transparent 36%,rgba(0,0,0,.9) 100%)}}
#grain{{position:fixed;inset:0;z-index:45;pointer-events:none;opacity:.025;
  animation:grn .12s steps(1) infinite}}
@keyframes grn{{0%{{transform:translate(0,0)}}25%{{transform:translate(-3px,2px)}}
  50%{{transform:translate(2px,-3px)}}75%{{transform:translate(-2px,-1px)}}}}
#pcv{{position:fixed;inset:0;z-index:44;pointer-events:none}}
#curt{{position:fixed;inset:0;z-index:48;background:var(--burg);pointer-events:none;
  clip-path:inset(0 100% 0 0)}}
#pb{{position:fixed;bottom:2px;left:0;height:1px;background:var(--rose);z-index:60;
  animation:pgr {LOOP}s linear infinite}}
@keyframes pgr{{from{{width:0}}to{{width:100%}}}}
.scene{{position:absolute;inset:0;overflow:hidden;opacity:0}}
.bg{{position:absolute;inset:-8%;background-size:cover;background-position:center;will-change:transform}}
.ov-l{{position:absolute;inset:0;background:linear-gradient(to right,rgba(42,15,28,.92) 0%,rgba(42,15,28,.06) 100%)}}
.ov-b{{position:absolute;inset:0;background:linear-gradient(to top,rgba(42,15,28,.97) 0%,rgba(42,15,28,.04) 55%)}}
.ov-dk{{position:absolute;inset:0}}
.cnt{{position:absolute;inset:0;display:flex;flex-direction:column;
  justify-content:center;padding:clamp(26px,4.8vw,86px);z-index:2}}
.cc{{align-items:center;text-align:center}}
.cb{{justify-content:flex-end;padding-bottom:clamp(46px,8.5vh,108px)}}
.lt{{position:absolute;top:clamp(18px,3.8vh,58px);left:0;right:0;
  height:clamp(14px,2.6vh,36px);background:url('{lace_src}') center/auto 100% repeat-x;
  opacity:.44;z-index:3;pointer-events:none}}
.lb{{position:absolute;bottom:clamp(18px,3.8vh,58px);left:0;right:0;
  height:clamp(14px,2.6vh,36px);background:url('{lace_src}') center/auto 100% repeat-x;
  opacity:.44;z-index:3;pointer-events:none;transform:scaleY(-1)}}
.lm{{overflow:hidden;display:block}}
.tag{{font-family:'Montserrat',sans-serif;font-weight:200;
  font-size:clamp(7px,.76vw,10px);letter-spacing:.7em;color:var(--rose);
  text-transform:uppercase;display:block;margin-bottom:.75em}}
.xl{{font-weight:300;font-size:clamp(46px,9.2vw,118px);line-height:.9;color:var(--cream);display:block}}
.lg{{font-weight:300;font-size:clamp(27px,4.6vw,70px);line-height:1;color:var(--cream);display:block}}
.it{{font-weight:300;font-style:italic;font-size:clamp(23px,4.2vw,58px);line-height:1.1;color:var(--cream);display:block}}
.sm{{font-family:'Montserrat',sans-serif;font-weight:200;
  font-size:clamp(7px,.92vw,12px);letter-spacing:.23em;
  color:rgba(253,245,240,.6);display:block;margin-top:.75em}}
.rl{{height:1px;background:var(--rose);opacity:.72;display:block}}
.lhtl{{font-family:'Montserrat',sans-serif;font-weight:200;
  font-size:clamp(9px,1.35vw,15px);letter-spacing:1em;color:var(--rose);display:block}}
.lnm{{font-weight:300;font-size:clamp(56px,12vw,144px);
  letter-spacing:.08em;color:var(--cream);display:block;line-height:1;
  animation:glow 5.5s ease-in-out 3s infinite}}
@keyframes glow{{0%,100%{{text-shadow:none}}
  50%{{text-shadow:0 0 50px rgba(196,136,154,.5),0 0 100px rgba(240,196,196,.2)}}}}
.lsub{{font-weight:300;font-style:italic;font-size:clamp(11px,1.6vw,20px);
  color:var(--pink);letter-spacing:.1em;display:block}}
.rmosaic{{position:absolute;right:0;top:0;bottom:0;width:42%;
  display:grid;grid-template-columns:1fr 1fr;gap:3px}}
.ri{{background-size:cover;background-position:center}}
.rfade{{position:absolute;inset:0;
  background:linear-gradient(to right,var(--dark) 43%,transparent 100%)}}
.rtxt{{position:absolute;left:0;top:50%;transform:translateY(-50%);
  padding:0 clamp(26px,4.8vw,86px);max-width:55%}}
.rrow{{border-bottom:1px solid rgba(196,136,154,.18);
  padding:clamp(8px,1.2vw,16px) 0;
  display:flex;justify-content:space-between;align-items:baseline;gap:14px}}
.rn{{font-weight:300;font-size:clamp(12px,1.55vw,19px);color:var(--cream)}}
.rp{{font-family:'Montserrat',sans-serif;font-weight:200;
  font-size:clamp(7px,.82vw,10px);color:var(--rose);letter-spacing:.08em;white-space:nowrap}}
.btn{{display:inline-block;border:1px solid var(--rose);padding:.7em 2.2em;
  font-family:'Montserrat',sans-serif;font-weight:300;
  font-size:clamp(7px,.92vw,11px);letter-spacing:.44em;
  color:var(--rose);text-transform:uppercase;margin-top:2.2em}}
.oh{{font-family:'Montserrat',sans-serif;font-weight:200;
  font-size:clamp(8px,1.15vw,14px);letter-spacing:1em;color:var(--rose);
  display:block;text-align:center;margin-bottom:.35em}}
.on{{font-weight:300;font-size:clamp(38px,8.5vw,110px);
  color:var(--cream);letter-spacing:.12em;display:block;text-align:center;line-height:1}}
.ou{{font-family:'Montserrat',sans-serif;font-weight:200;
  font-size:clamp(7px,.92vw,12px);letter-spacing:.3em;
  color:rgba(196,136,154,.66);display:block;text-align:center}}
.wvs{{position:absolute;bottom:0;left:0;width:100%;height:20%;z-index:1;pointer-events:none}}
.wv{{position:absolute;bottom:0;width:200%;height:100%}}
.wv1{{animation:wm 9s ease-in-out infinite;opacity:.17}}
.wv2{{animation:wm 7s ease-in-out infinite reverse;opacity:.12;bottom:-5px}}
@keyframes wm{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(-25%)}}}}
/* scene timing — generated by Python */
{css_kf}
</style>
</head>
<body>
<div id="curt"></div>
<canvas id="pcv"></canvas>
<div id="grain"><svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
  <filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="4" stitchTiles="stitch"/></filter>
  <rect width="100%" height="100%" filter="url(#n)"/>
</svg></div>
<div id="vig"></div>
<div id="pb"></div>

{scenes_html}

<script>
{js}
</script>
</body>
</html>"""

    OUT.write_text(html, encoding='utf-8')
    size_kb = OUT.stat().st_size // 1024
    print(f"\n✅ Output: {OUT}", file=sys.stderr)
    print(f"   Size  : {size_kb} KB ({size_kb/1024:.1f} MB)", file=sys.stderr)
    print(f"   Scenes: {len(SCENES)}", file=sys.stderr)
    print(f"   Self-contained: YES (no img/ folder needed)", file=sys.stderr)

if __name__ == '__main__':
    build()
