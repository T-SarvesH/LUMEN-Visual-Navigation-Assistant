import time

class SceneryManager:
    def __init__(self, interval=30, frame_w=1280, frame_h=720):
        self.interval = interval
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.last_update_time = 0
        
        self.V_BREAK = 0.6  
        self.H_BREAKS = [0.33, 0.66]

    def get_coa_zone(self, bbox):
        x1, y1, x2, y2 = bbox
        coa_x = (x1 + x2) / 2
        coa_y = (y1 + y2) / 2
        
        # Vertical: Far vs Immediate
        v = "Far" if coa_y < self.frame_h * self.V_BREAK else "Immediate"
        
        # Horizontal: Left, Center, Right
        if coa_x < self.frame_w * self.H_BREAKS[0]: h = "Left"
        elif coa_x < self.frame_w * self.H_BREAKS[1]: h = "Forward"
        else: h = "Right"
        
        return v, h

    def generate_refined_json(self, tracks, class_lookup, priority_override=False):
        now = time.time()
        
        if not priority_override and (now - self.last_update_time < self.interval):
            return None
            
        self.last_update_time = now
        
        refined_json = {
            "scenery": {},
            "metadata": {"is_priority": priority_override}
        }
        
        for track in tracks:
            x1, y1, x2, y2, tid, conf, cid = track[:7]
            if conf < 0.45: continue 
            
            label = cid if isinstance(cid, str) else class_lookup.get(int(cid), "object") 
            v, h = self.get_coa_zone((x1, y1, x2, y2))
            
            if label not in refined_json["scenery"]:
                refined_json["scenery"][label] = {
                    "Immediate Forward": 0, "Far Forward": 0,
                    "Left": 0, "Right": 0,
                    "Far Left": 0, "Far Right": 0
                }
            
            # Mapping 2x3 Grid into your specific Refined categories
            if v == "Immediate":
                if h == "Forward": refined_json["scenery"][label]["Immediate Forward"] += 1
                elif h == "Left": refined_json["scenery"][label]["Left"] += 1
                else: refined_json["scenery"][label]["Right"] += 1
            else: # v == "Far"
                if h == "Forward": refined_json["scenery"][label]["Far Forward"] += 1
                elif h == "Left": refined_json["scenery"][label]["Far Left"] += 1
                else: refined_json["scenery"][label]["Far Right"] += 1
            
        return refined_json

    def prepare_llm_input(self, refined_json):
        if not refined_json: return None
        prompt_parts = []
        for obj, zones in refined_json["scenery"].items():
            for zone, count in zones.items():
                if count > 0:
                    prompt_parts.append(f"{count} {obj}(s) {zone}")
        return "Scene: " + ", ".join(prompt_parts) + "."