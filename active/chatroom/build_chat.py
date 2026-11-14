import json, os, glob, sys
here = os.path.dirname(os.path.abspath(__file__))
agents = [
 ("Agent A","FocusPage Advocate","Makes the strongest honest case for FocusPage (CVI picture books)"),
 ("Agent B","Crosscheck Advocate","Makes the strongest honest case for Crosscheck (medication label verification)"),
 ("Agent C","Receipts Advocate","Makes the strongest honest case for Receipts (transcript checker)"),
 ("Agent D","LectureLens Advocate","Makes the strongest honest case for LectureLens (course-aware captions)"),
 ("Agent E","Hackathon Judge","Neutral judge scoring on Innovation/Functionality/Practicality/Presentation"),
 ("Agent F","Critic","Adversarial: failure modes, competitor overlap, ethics, demo risks"),
]
rounds=[]
for r in range(1,10):
    files = sorted(glob.glob(os.path.join(here,f"r{r}_*.md")))
    if not files: break
    entries=[]
    for name,role,_ in agents:
        p=os.path.join(here,f"r{r}_{name[-1]}.md")
        if os.path.exists(p):
            entries.append({"agent":name,"role":role,"response":open(p).read().strip()})
    rounds.append({"round":r,"entries":entries})
prev = json.load(open(os.path.join(here,"chat.json"))) if os.path.exists(os.path.join(here,"chat.json")) else {}
chat={"problem":"Choose one of four HackUMass XIV ideas (FocusPage, Crosscheck, Receipts, LectureLens) and note potential fixes for each; pivots/merges allowed.",
 "context":"See ideas.md in this directory.",
 "agents":[{"name":n,"role":r,"framing":f} for n,r,f in agents],
 "rounds":rounds,"final_output":prev.get("final_output")}
json.dump(chat,open(os.path.join(here,"chat.json"),"w"),indent=2)
print("rounds:",len(rounds),[len(x["entries"]) for x in rounds])
