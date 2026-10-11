"""Draws deck/dancing_cat.gif, an original cartoon tabby, 24 frames, transparent background. Run with the project venv."""
from PIL import Image, ImageDraw
import math, os
N=24; SZ=512; S=4; W=3600
FUR=(245,158,66); FUR2=(226,128,40); STRIPE=(196,98,28); CREAM=(255,236,205); DARK=(40,34,30); PINK=(255,150,170); WHITE=(255,255,255); CYAN=(34,211,238); IRIS=(70,160,90)
def E(d,cx,cy,rx,ry,fill): d.ellipse([cx-rx,cy-ry,cx+rx,cy+ry],fill=fill)
frames=[]
for i in range(N):
    t=2*math.pi*i/N
    im=Image.new("RGBA",(W,W),(0,0,0,0)); d=ImageDraw.Draw(im)
    sway=60*S*math.sin(t); bounce=-abs(40*S*math.sin(2*t)); cx=W/2+sway; cy=W*0.62+bounce
    for k in range(18):
        a=k/18; px=cx+120*S+a*160*S; py=cy+40*S-a*240*S+math.sin(t*2+a*3)*40*S*a
        E(d,px,py,(22-a*10)*S,(22-a*10)*S,FUR2)
    for sx in (-1,1):
        fx=cx+sx*70*S+sx*8*S*math.sin(t*2); E(d,fx,cy+150*S,46*S,30*S,FUR); E(d,fx,cy+156*S,30*S,16*S,CREAM)
    E(d,cx,cy+30*S,130*S,150*S,FUR)
    for k in range(3):
        y=cy-20*S+k*55*S; d.arc([cx-128*S,y-30*S,cx-20*S,y+30*S],200,330,fill=STRIPE,width=14*S); d.arc([cx+20*S,y-30*S,cx+128*S,y+30*S],210,340,fill=STRIPE,width=14*S)
    E(d,cx,cy+55*S,80*S,105*S,CREAM)
    for sx,ph in ((-1,0),(1,math.pi)):
        up=max(0,math.sin(2*t+ph)); ax=cx+sx*(150+40*up)*S; ay=cy-(20+170*up)*S+(0 if up else 50*S)
        d.line([cx+sx*95*S,cy+10*S,ax,ay],fill=FUR,width=46*S); E(d,ax,ay,30*S,30*S,FUR); E(d,ax,ay,16*S,16*S,CREAM)
    HL=1400; hl=Image.new("RGBA",(HL,HL),(0,0,0,0)); h=ImageDraw.Draw(hl); hx=hy=HL/2; R=150*S
    for sx in (-1,1):
        h.polygon([(hx+sx*60*S,hy-110*S),(hx+sx*150*S,hy-250*S),(hx+sx*150*S,hy-80*S)],fill=FUR)
        h.polygon([(hx+sx*75*S,hy-120*S),(hx+sx*135*S,hy-215*S),(hx+sx*135*S,hy-100*S)],fill=PINK)
    E(h,hx,hy,R,R*0.9,FUR)
    for sx in (-1,1):
        for k in range(3): h.line([hx+sx*(20+k*28)*S,hy-130*S+k*6*S,hx+sx*(10+k*28)*S,hy-70*S],fill=STRIPE,width=12*S)
    E(h,hx,hy+55*S,95*S,65*S,CREAM)
    blink = i in (5,17)
    for sx in (-1,1):
        ex,ey=hx+sx*60*S,hy-15*S
        if blink: h.line([ex-28*S,ey,ex+28*S,ey],fill=DARK,width=10*S)
        else: E(h,ex,ey,34*S,40*S,WHITE); E(h,ex+sx*4*S,ey+6*S,20*S,26*S,IRIS); E(h,ex+sx*4*S,ey+6*S,11*S,16*S,DARK); E(h,ex-8*S,ey-10*S,8*S,8*S,WHITE)
    h.polygon([(hx-16*S,hy+32*S),(hx+16*S,hy+32*S),(hx,hy+50*S)],fill=PINK)
    h.arc([hx-40*S,hy+40*S,hx,hy+80*S],10,170,fill=DARK,width=8*S); h.arc([hx,hy+40*S,hx+40*S,hy+80*S],10,170,fill=DARK,width=8*S)
    for sx in (-1,1):
        for dy,ang in ((-5,-12),(15,0),(35,12)):
            x0,y0=hx+sx*70*S,hy+(40+dy)*S; L=150*S; a=math.radians(ang); h.line([x0,y0,x0+sx*L*math.cos(a),y0+L*math.sin(a)],fill=DARK,width=6*S)
    hl=hl.rotate(-12*math.sin(t),resample=Image.BICUBIC)
    im.paste(hl,(int(cx-HL/2),int(cy-215*S-HL/2)),hl)
    bx,by=cx,cy-55*S                                                      # bow tie, below the chin
    d.polygon([(bx,by),(bx-45*S,by-28*S),(bx-45*S,by+28*S)],fill=CYAN); d.polygon([(bx,by),(bx+45*S,by-28*S),(bx+45*S,by+28*S)],fill=CYAN); E(d,bx,by,14*S,14*S,(20,160,190))
    for sx,ph in ((-1,0),(1,0.5)):
        f=((i/N+ph)%1); nx=cx+sx*330*S+sx*20*S*math.sin(t); ny=cy-250*S-f*300*S; op=int(255*(1-f))
        nl=Image.new("RGBA",(W,W),(0,0,0,0)); n=ImageDraw.Draw(nl); n.ellipse([nx-18*S,ny,nx+18*S,ny+28*S],fill=(255,255,255,op)); n.line([nx+16*S,ny+14*S,nx+16*S,ny-60*S],fill=(255,255,255,op),width=8*S); n.line([nx+16*S,ny-60*S,nx+46*S,ny-45*S],fill=(255,255,255,op),width=8*S)
        im.alpha_composite(nl)
    frames.append(im.resize((SZ,SZ),Image.LANCZOS))
out=[]
for fr in frames:
    comp=Image.alpha_composite(Image.new("RGBA",fr.size,(10,15,30,255)),fr).convert("RGB")
    p=comp.convert("P",palette=Image.ADAPTIVE,colors=255); pal=p.getpalette(); mask=fr.split()[3].point(lambda a:255 if a<64 else 0)
    p.paste(255,mask=mask); pal[255*3:255*3+3]=[10,15,30]; p.putpalette(pal); out.append(p)
here=os.path.dirname(os.path.abspath(__file__))
out[0].save(os.path.join(here,"dancing_cat.gif"),save_all=True,append_images=out[1:],duration=55,loop=0,transparency=255,disposal=2,optimize=False)
frames[0].convert("RGB").save(os.path.join(here,"dancing_cat.png"))
print("dancing_cat.gif written")
