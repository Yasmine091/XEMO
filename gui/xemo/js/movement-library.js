// XEMO's reusable body vocabulary. Values are deliberately conservative and
// expressed in the relay's normalized wheel range (-1..1) plus arm degrees.
export const MOVEMENTS={
  forward_short:{label:"careful short advance",surface:"floor",navigation:true,steps:[
    {left:.24,right:.24,arm:135,ms:600}]},
  forward_medium:{label:"steady short advance",surface:"floor",navigation:true,steps:[
    {left:.25,right:.25,arm:135,ms:1150}]},
  backward_short:{label:"careful short retreat",surface:"floor",navigation:true,steps:[
    {left:-.24,right:-.24,arm:135,ms:600}]},
  pivot_left:{label:"small pivot left",surface:"floor",navigation:true,steps:[
    {left:-.38,right:.38,arm:135,ms:520}]},
  pivot_right:{label:"small pivot right",surface:"floor",navigation:true,steps:[
    {left:.38,right:-.38,arm:135,ms:520}]},
  arc_left:{label:"curved path left",surface:"floor",navigation:true,steps:[
    {left:.14,right:.34,arm:135,ms:700}]},
  arc_right:{label:"curved path right",surface:"floor",navigation:true,steps:[
    {left:.34,right:.14,arm:135,ms:700}]},
  arc_left_long:{label:"longer curved path left",surface:"floor",navigation:true,steps:[
    {left:.14,right:.34,arm:135,ms:1100},{left:0,right:0,arm:135,ms:240}]},
  arc_right_long:{label:"longer curved path right",surface:"floor",navigation:true,steps:[
    {left:.34,right:.14,arm:135,ms:1100},{left:0,right:0,arm:135,ms:240}]},
  scan_left:{label:"look around left",surface:"floor",navigation:true,steps:[
    {left:-.3,right:.3,arm:135,ms:720}]},
  scan_right:{label:"look around right",surface:"floor",navigation:true,steps:[
    {left:.3,right:-.3,arm:135,ms:720}]},
  stop:{label:"full stop",surface:"any",navigation:true,steps:[
    {left:0,right:0,arm:135,ms:120}]},
  wave:{label:"friendly wave",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:135,ms:420},{left:0,right:0,arm:135,armRight:270,ms:420},
    {left:0,right:0,arm:270,armRight:135,ms:420},{left:0,right:0,arm:135,armRight:135,ms:360}]},
  arm_flap:{label:"happy arm flap",surface:"any",steps:[
    {left:0,right:0,arm:270,ms:360},{left:0,right:0,arm:135,ms:360},
    {left:0,right:0,arm:270,ms:360},{left:0,right:0,arm:135,ms:360},
    {left:0,right:0,arm:135,ms:360}]},
  dance:{label:"playful dance",surface:"floor",steps:[
    {left:.48,right:-.48,arm:270,ms:480},{left:-.48,right:.48,arm:135,ms:480},
    {left:.48,right:-.48,arm:270,ms:480},{left:0,right:0,arm:135,ms:420}]},
  wiggle:{label:"small wiggle",surface:"floor",steps:[
    {left:.42,right:-.42,arm:110,ms:360},{left:-.42,right:.42,arm:160,ms:360},
    {left:.42,right:-.42,arm:110,ms:360},{left:0,right:0,arm:135,ms:360}]},
  celebrate:{label:"celebration",surface:"floor",steps:[
    {left:.5,right:-.5,arm:270,ms:420},{left:-.5,right:.5,arm:135,ms:420},
    {left:0,right:0,arm:270,ms:360},{left:0,right:0,arm:135,ms:360}]},
  sway:{label:"gentle sway",surface:"floor",steps:[
    {left:.34,right:-.34,arm:110,ms:520},{left:-.34,right:.34,arm:160,ms:520},
    {left:0,right:0,arm:135,ms:400}]},
  left_wheel_twice:{label:"left wheel twice",surface:"floor",steps:[
    {left:.48,right:0,arm:135,ms:520},{left:0,right:0,arm:135,ms:260},
    {left:.48,right:0,arm:135,ms:520},{left:0,right:0,arm:135,ms:260}]},
  right_wheel_twice:{label:"right wheel twice",surface:"floor",steps:[
    {left:0,right:.48,arm:135,ms:520},{left:0,right:0,arm:135,ms:260},
    {left:0,right:.48,arm:135,ms:520},{left:0,right:0,arm:135,ms:260}]}
  ,left_wheel_once:{label:"left wheel once",surface:"floor",navigation:true,steps:[
    {left:.48,right:0,arm:135,ms:520},{left:0,right:0,arm:135,ms:260}]}
  ,right_wheel_once:{label:"right wheel once",surface:"floor",navigation:true,steps:[
    {left:0,right:.48,arm:135,ms:520},{left:0,right:0,arm:135,ms:260}]}
  ,tiny_bow:{label:"tiny bow",surface:"any",steps:[
    {left:0,right:0,arm:65,ms:360},{left:0,right:0,arm:115,ms:360},
    {left:0,right:0,arm:135,ms:360}]}
  ,shy_peek:{label:"shy peek",surface:"floor",steps:[
    {left:-.28,right:-.28,arm:55,ms:360},{left:.28,right:.28,arm:125,ms:360},
    {left:0,right:0,arm:135,ms:360}]}
  ,look_around:{label:"look around",surface:"floor",steps:[
    {left:.38,right:-.38,arm:135,ms:420},{left:-.38,right:.38,arm:135,ms:420},
    {left:0,right:0,arm:135,ms:300}]}
  ,curious_peek:{label:"curious peek",surface:"floor",steps:[
    {left:.24,right:.24,arm:70,ms:360},{left:-.24,right:-.24,arm:110,ms:360},
    {left:0,right:0,arm:135,ms:360}]}
  ,retreat_gently:{label:"gentle retreat",surface:"floor",steps:[
    {left:-.24,right:-.24,arm:135,ms:520},{left:0,right:0,arm:135,ms:260}]}
  ,wiggle_arms:{label:"two-arm wiggle",surface:"any",steps:[
    {left:0,right:0,arm:65,armRight:205,ms:320},{left:0,right:0,arm:125,armRight:145,ms:320},
    {left:0,right:0,arm:65,armRight:205,ms:320},{left:0,right:0,arm:135,armRight:135,ms:360}]}
  ,hello_big:{label:"big hello",surface:"any",steps:[
    {left:0,right:0,arm:35,armRight:135,ms:360},{left:0,right:0,arm:135,armRight:35,ms:360},
    {left:0,right:0,arm:35,armRight:135,ms:360},{left:0,right:0,arm:135,armRight:35,ms:360}]}
  ,stretch:{label:"full-body stretch",surface:"any",steps:[
    {left:0,right:0,arm:15,armRight:255,ms:650},{left:0,right:0,arm:135,armRight:135,ms:500}]}
  ,shrug:{label:"tiny shrug",surface:"any",steps:[
    {left:0,right:0,arm:95,armRight:95,ms:260},{left:0,right:0,arm:165,armRight:165,ms:360},
    {left:0,right:0,arm:135,armRight:135,ms:360}]}
  ,clap:{label:"clap",surface:"any",steps:[
    {left:0,right:0,arm:55,armRight:215,ms:300},{left:0,right:0,arm:135,armRight:135,ms:260},
    {left:0,right:0,arm:55,armRight:215,ms:300},{left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,cheer:{label:"cheer",surface:"any",steps:[
    {left:0,right:0,arm:10,armRight:260,ms:380},{left:0,right:0,arm:135,armRight:135,ms:300},
    {left:0,right:0,arm:10,armRight:260,ms:380}]}
  ,point_left:{label:"point left",surface:"any",steps:[
    {left:0,right:0,arm:35,armRight:135,ms:500},{left:0,right:0,arm:135,armRight:135,ms:500}]}
  ,point_right:{label:"point right",surface:"any",steps:[
    {left:0,right:0,arm:135,armRight:35,ms:500},{left:0,right:0,arm:135,armRight:135,ms:500}]}
  ,peek_left:{label:"peek left",surface:"floor",steps:[
    {left:-.2,right:.2,arm:135,armRight:135,ms:420},{left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,peek_right:{label:"peek right",surface:"floor",steps:[
    {left:.2,right:-.2,arm:135,armRight:135,ms:420},{left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,circle_left:{label:"small circle left",surface:"floor",navigation:true,steps:[
    {left:-.38,right:.5,arm:110,armRight:160,ms:650},{left:.5,right:-.38,arm:160,armRight:110,ms:650},
    {left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,circle_right:{label:"small circle right",surface:"floor",navigation:true,steps:[
    {left:.5,right:-.38,arm:160,armRight:110,ms:650},{left:-.38,right:.5,arm:110,armRight:160,ms:650},
    {left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,figure_eight:{label:"small figure eight",surface:"floor",navigation:true,steps:[
    {left:.42,right:-.3,arm:120,armRight:150,ms:600},{left:-.3,right:.42,arm:150,armRight:120,ms:600},
    {left:-.42,right:.3,arm:120,armRight:150,ms:600},{left:.3,right:-.42,arm:150,armRight:120,ms:600},
    {left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,robot:{label:"robot pose",surface:"any",steps:[
    {left:0,right:0,arm:20,armRight:250,ms:450},{left:0,right:0,arm:135,armRight:135,ms:450},
    {left:0,right:0,arm:250,armRight:20,ms:450},{left:0,right:0,arm:135,armRight:135,ms:450}]}
  ,shiver:{label:"playful shiver",surface:"any",steps:[
    {left:0,right:0,arm:120,armRight:150,ms:150},{left:0,right:0,arm:150,armRight:120,ms:150},
    {left:0,right:0,arm:120,armRight:150,ms:150},{left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,reverse_turn:{label:"reverse and turn",surface:"floor",navigation:true,steps:[
    {left:-.3,right:-.3,arm:135,armRight:135,ms:500},{left:-.45,right:.45,arm:135,armRight:135,ms:600},
    {left:0,right:0,arm:135,armRight:135,ms:250}]}
  ,arms_down:{label:"arms down",surface:"any",steps:[
    {left:0,right:0,arm:135,armRight:135,ms:450}]}
  ,arms_up:{label:"arms up",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:270,ms:600}]}
  ,arms_open:{label:"arms open",surface:"any",steps:[
    {left:0,right:0,arm:15,armRight:255,ms:600}]}
  ,arms_close:{label:"arms close/back",surface:"any",steps:[
    {left:0,right:0,arm:0,armRight:0,ms:500}]}
  ,arms_back:{label:"arms back",surface:"any",steps:[
    {left:0,right:0,arm:0,armRight:0,ms:600}]}
  ,arms_cross:{label:"arms cross",surface:"any",steps:[
    {left:0,right:0,arm:35,armRight:35,ms:550},{left:0,right:0,arm:135,armRight:135,ms:450}]}
  ,salute:{label:"salute",surface:"any",steps:[
    {left:0,right:0,arm:135,armRight:35,ms:500},{left:0,right:0,arm:135,armRight:135,ms:450}]}
  ,up_down:{label:"arms up then down",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:270,ms:600},{left:0,right:0,arm:135,armRight:135,ms:600}]}
  ,arms_together:{label:"bring arms together",surface:"any",steps:[
    {left:0,right:0,arm:20,armRight:250,ms:500},{left:0,right:0,arm:125,armRight:145,ms:500}]}
  ,arms_apart:{label:"move arms apart",surface:"any",steps:[
    {left:0,right:0,arm:125,armRight:145,ms:500},{left:0,right:0,arm:20,armRight:250,ms:500}]}
  ,high_five:{label:"high five",surface:"any",steps:[
    {left:0,right:0,arm:135,armRight:20,ms:550},{left:0,right:0,arm:135,armRight:135,ms:450}]}
  ,beckon:{label:"beckon closer",surface:"any",steps:[
    {left:0,right:0,arm:70,armRight:200,ms:300},{left:0,right:0,arm:135,armRight:135,ms:260},
    {left:0,right:0,arm:70,armRight:200,ms:300},{left:0,right:0,arm:135,armRight:135,ms:260}]}
  ,hug:{label:"hug",surface:"any",steps:[
    {left:0,right:0,arm:20,armRight:250,ms:450},{left:0,right:0,arm:115,armRight:155,ms:550},
    {left:0,right:0,arm:135,armRight:135,ms:350}]}
  ,apology_bow:{label:"apology bow",surface:"any",steps:[
    {left:0,right:0,arm:95,armRight:175,ms:380},{left:0,right:0,arm:135,armRight:135,ms:450}]}
  ,sleepy:{label:"sleepy droop",surface:"any",steps:[
    {left:0,right:0,arm:150,armRight:120,ms:650},{left:0,right:0,arm:135,armRight:135,ms:500}]}
  ,excited_bounce:{label:"excited bounce",surface:"floor",steps:[
    {left:.28,right:.28,arm:35,armRight:235,ms:260},{left:-.22,right:-.22,arm:135,armRight:135,ms:220},
    {left:.28,right:.28,arm:35,armRight:235,ms:260},{left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,inch_forward:{label:"tiny careful advance",surface:"floor",navigation:true,steps:[
    {left:.18,right:.18,arm:135,armRight:135,ms:280},{left:0,right:0,arm:135,armRight:135,ms:220}]}
  ,inch_backward:{label:"tiny careful retreat",surface:"floor",navigation:true,steps:[
    {left:-.18,right:-.18,arm:135,armRight:135,ms:280},{left:0,right:0,arm:135,armRight:135,ms:220}]}
  ,quick_turn_left:{label:"quick turn left",surface:"floor",navigation:true,steps:[
    {left:-.48,right:.48,arm:135,armRight:135,ms:700},{left:0,right:0,arm:135,armRight:135,ms:250}]}
  ,quick_turn_right:{label:"quick turn right",surface:"floor",navigation:true,steps:[
    {left:.48,right:-.48,arm:135,armRight:135,ms:700},{left:0,right:0,arm:135,armRight:135,ms:250}]}
  ,zigzag:{label:"small zigzag",surface:"floor",navigation:true,steps:[
    {left:.18,right:.4,arm:120,armRight:150,ms:500},{left:.4,right:.18,arm:150,armRight:120,ms:500},
    {left:.18,right:.4,arm:120,armRight:150,ms:500},{left:0,right:0,arm:135,armRight:135,ms:250}]}
  ,cautious_scan:{label:"cautious scan",surface:"floor",navigation:true,steps:[
    {left:-.22,right:.22,arm:135,armRight:135,ms:500},{left:.22,right:-.22,arm:135,armRight:135,ms:1000},
    {left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,wave_right:{label:"friendly right-arm wave",surface:"any",steps:[
    {left:0,right:0,armRight:270,ms:420},{left:0,right:0,armRight:135,ms:420},
    {left:0,right:0,armRight:270,ms:420},{left:0,right:0,armRight:135,ms:360}]}
  ,wave_left:{label:"friendly left-arm wave",surface:"any",steps:[
    {left:0,right:0,arm:270,armBoth:false,ms:420},{left:0,right:0,arm:135,armBoth:false,ms:420},
    {left:0,right:0,arm:270,armBoth:false,ms:420},{left:0,right:0,arm:135,armBoth:false,ms:360}]}
  ,raise_left:{label:"raise left arm",surface:"any",steps:[
    {left:0,right:0,arm:270,armBoth:false,ms:550}]}
  ,raise_right:{label:"raise right arm",surface:"any",steps:[
    {left:0,right:0,armRight:270,ms:550}]}
  ,lower_left:{label:"lower left arm",surface:"any",steps:[
    {left:0,right:0,arm:135,armBoth:false,ms:450}]}
  ,lower_right:{label:"lower right arm",surface:"any",steps:[
    {left:0,right:0,armRight:135,ms:450}]}
  ,back_left:{label:"move left arm back",surface:"any",steps:[
    {left:0,right:0,arm:0,armBoth:false,ms:550}]}
  ,back_right:{label:"move right arm back",surface:"any",steps:[
    {left:0,right:0,armRight:0,ms:550}]}
  ,single_arm_sweep_left:{label:"sweep only the left arm",surface:"any",steps:[
    {left:0,right:0,arm:0,armBoth:false,ms:350},{left:0,right:0,arm:135,armBoth:false,ms:350},
    {left:0,right:0,arm:270,armBoth:false,ms:500},{left:0,right:0,arm:135,armBoth:false,ms:350}]}
  ,single_arm_sweep_right:{label:"sweep only the right arm",surface:"any",steps:[
    {left:0,right:0,armRight:0,ms:350},{left:0,right:0,armRight:135,ms:350},
    {left:0,right:0,armRight:270,ms:500},{left:0,right:0,armRight:135,ms:350}]}
  ,double_wave:{label:"wave with both arms together",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:270,ms:420},{left:0,right:0,arm:135,armRight:135,ms:420},
    {left:0,right:0,arm:270,armRight:270,ms:420},{left:0,right:0,arm:135,armRight:135,ms:360}]}
  ,alternating_raise:{label:"alternate arm raises",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:135,ms:500},{left:0,right:0,arm:135,armRight:270,ms:500},
    {left:0,right:0,arm:270,armRight:135,ms:500},{left:0,right:0,arm:135,armRight:135,ms:350}]}
  ,different_angles:{label:"hold both arms at different angles",surface:"any",steps:[
    {left:0,right:0,arm:0,armRight:270,ms:600},{left:0,right:0,arm:90,armRight:210,ms:600},
    {left:0,right:0,arm:135,armRight:135,ms:450}]}
  ,mirror_sweep:{label:"sweep arms in opposite directions",surface:"any",steps:[
    {left:0,right:0,arm:0,armRight:270,ms:450},{left:0,right:0,arm:135,armRight:135,ms:350},
    {left:0,right:0,arm:270,armRight:0,ms:450},{left:0,right:0,arm:135,armRight:135,ms:350}]}
  ,staggered_pose:{label:"staggered arm pose",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:90,ms:650},{left:0,right:0,arm:90,armRight:270,ms:650},
    {left:0,right:0,arm:135,armRight:135,ms:400}]}
  ,pulse_left:{label:"pulse the left arm",surface:"any",steps:[
    {left:0,right:0,arm:270,armBoth:false,ms:240},{left:0,right:0,arm:135,armBoth:false,ms:240},
    {left:0,right:0,arm:270,armBoth:false,ms:240},{left:0,right:0,arm:135,armBoth:false,ms:300}]}
  ,pulse_right:{label:"pulse the right arm",surface:"any",steps:[
    {left:0,right:0,armRight:270,ms:240},{left:0,right:0,armRight:135,ms:240},
    {left:0,right:0,armRight:270,ms:240},{left:0,right:0,armRight:135,ms:300}]}
  ,ripple_raise:{label:"ripple arms upward",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:135,ms:400},{left:0,right:0,arm:135,armRight:270,ms:400},
    {left:0,right:0,arm:270,armRight:270,ms:400},{left:0,right:0,arm:135,armRight:135,ms:400}]}
  ,ripple_back:{label:"ripple arms backward",surface:"any",steps:[
    {left:0,right:0,arm:0,armRight:135,ms:400},{left:0,right:0,arm:135,armRight:0,ms:400},
    {left:0,right:0,arm:0,armRight:0,ms:400},{left:0,right:0,arm:135,armRight:135,ms:400}]}
  ,staircase_raise:{label:"step both arms upward",surface:"any",steps:[
    {left:0,right:0,arm:90,armRight:90,ms:350},{left:0,right:0,arm:135,armRight:135,ms:350},
    {left:0,right:0,arm:210,armRight:210,ms:350},{left:0,right:0,arm:270,armRight:270,ms:450}]}
  ,staircase_lower:{label:"step both arms downward",surface:"any",steps:[
    {left:0,right:0,arm:210,armRight:210,ms:350},{left:0,right:0,arm:135,armRight:135,ms:350},
    {left:0,right:0,arm:90,armRight:90,ms:350},{left:0,right:0,arm:0,armRight:0,ms:450}]}
  ,open_close:{label:"open and close arms",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:270,ms:500},{left:0,right:0,arm:0,armRight:0,ms:500},
    {left:0,right:0,arm:135,armRight:135,ms:400}]}
  ,back_to_up:{label:"back to up pose",surface:"any",steps:[
    {left:0,right:0,arm:0,armRight:0,ms:450},{left:0,right:0,arm:135,armRight:135,ms:350},
    {left:0,right:0,arm:270,armRight:270,ms:550}]}
  ,up_to_back:{label:"up to back pose",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:270,ms:450},{left:0,right:0,arm:135,armRight:135,ms:350},
    {left:0,right:0,arm:0,armRight:0,ms:550}]}
  ,left_point_right_back:{label:"point left and hold right back",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:0,ms:650},{left:0,right:0,arm:135,armRight:135,ms:450}]}
  ,right_point_left_back:{label:"point right and hold left back",surface:"any",steps:[
    {left:0,right:0,arm:0,armRight:270,ms:650},{left:0,right:0,arm:135,armRight:135,ms:450}]}
  ,cross_open:{label:"cross then open arms",surface:"any",steps:[
    {left:0,right:0,arm:35,armRight:35,ms:500},{left:0,right:0,arm:270,armRight:270,ms:550},
    {left:0,right:0,arm:135,armRight:135,ms:400}]}
  ,salute_switch:{label:"alternate salutes",surface:"any",steps:[
    {left:0,right:0,arm:270,armRight:135,ms:500},{left:0,right:0,arm:135,armRight:270,ms:500},
    {left:0,right:0,arm:270,armRight:135,ms:500},{left:0,right:0,arm:135,armRight:135,ms:350}]}
  ,slow_bilateral:{label:"slow synchronized arm sweep",surface:"any",steps:[
    {left:0,right:0,arm:0,armRight:0,ms:500},{left:0,right:0,arm:90,armRight:90,ms:500},
    {left:0,right:0,arm:180,armRight:180,ms:500},{left:0,right:0,arm:270,armRight:270,ms:650},
    {left:0,right:0,arm:135,armRight:135,ms:500}]}
  ,greeting_sequence:{label:"greeting sequence",surface:"any",steps:[
    {left:0,right:0,arm:135,armRight:135,ms:300},{left:0,right:0,arm:270,armBoth:false,ms:450},
    {left:0,right:0,arm:135,armBoth:false,ms:250},{left:0,right:0,arm:270,armBoth:false,ms:450},
    {left:0,right:0,arm:135,armRight:135,ms:350}]}
  ,celebration_sequence:{label:"celebration sequence",surface:"floor",steps:[
    {left:.35,right:-.35,arm:270,armRight:270,ms:450},{left:-.35,right:.35,arm:135,armRight:135,ms:350},
    {left:.35,right:-.35,arm:270,armRight:270,ms:450},{left:0,right:0,arm:135,armRight:135,ms:350}]}
  ,curious_scan_arms:{label:"curious scan with arms",surface:"floor",navigation:true,steps:[
    {left:-.25,right:.25,arm:270,armRight:135,ms:550},{left:.25,right:-.25,arm:135,armRight:270,ms:700},
    {left:0,right:0,arm:135,armRight:135,ms:350}]}
  ,retreat_and_wave:{label:"retreat then wave",surface:"floor",navigation:true,steps:[
    {left:-.25,right:-.25,arm:135,armRight:135,ms:550},{left:0,right:0,arm:270,armBoth:false,ms:450},
    {left:0,right:0,arm:135,armBoth:false,ms:350}]}
  ,dance_wave_combo:{label:"dance and wave combo",surface:"floor",steps:[
    {left:.4,right:-.4,arm:270,armRight:135,ms:450},{left:-.4,right:.4,arm:135,armRight:270,ms:450},
    {left:.4,right:-.4,arm:270,armRight:135,ms:450},{left:0,right:0,arm:135,armRight:135,ms:350}]}
  ,happy_walk:{label:"happy walk with expressive arms",surface:"floor",navigation:true,steps:[
    {left:.3,right:.3,arm:270,armRight:135,ms:500},{left:.3,right:.3,arm:135,armRight:270,ms:500},
    {left:.3,right:.3,arm:270,armRight:135,ms:500},{left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,signal_left:{label:"move forward while signaling left",surface:"floor",navigation:true,steps:[
    {left:.25,right:.25,arm:270,armBoth:false,ms:650},{left:0,right:0,arm:135,armBoth:false,ms:300}]}
  ,signal_right:{label:"move forward while signaling right",surface:"floor",navigation:true,steps:[
    {left:.25,right:.25,armRight:270,ms:650},{left:0,right:0,armRight:135,ms:300}]}
  ,welcoming_walk:{label:"welcoming walk with both arms",surface:"floor",navigation:true,steps:[
    {left:.22,right:.22,arm:270,armRight:270,ms:500},{left:.22,right:.22,arm:135,armRight:135,ms:400},
    {left:.22,right:.22,arm:270,armRight:270,ms:500},{left:0,right:0,arm:135,armRight:135,ms:300}]}
  ,victory:{label:"victory pose",surface:"any",steps:[
    {left:0,right:0,arm:20,armRight:250,ms:500},{left:0,right:0,arm:35,armRight:235,ms:280},
    {left:0,right:0,arm:20,armRight:250,ms:280}]}
};

// A shorthand `arm` in a built-in expressive movement means both arms.
// Navigation movements intentionally leave the unspecified arm untouched.
for (const movement of Object.values(MOVEMENTS)) {
  if (movement.navigation) continue;
  for (const step of movement.steps || []) {
    if (step.arm != null && step.armRight == null && step.armBoth == null) step.armBoth = true;
  }
}

const clamp = (value, min, max, fallback) => {
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
};

const copyStep = step => {
  const out = {
    left: clamp(step?.left, -1, 1, 0),
    right: clamp(step?.right, -1, 1, 0),
    ms: clamp(step?.ms, 120, 1800, 360)
  };
  if (step?.arm != null) out.arm = clamp(step.arm, 0, 270, 135);
  if (step?.armRight != null) out.armRight = clamp(step.armRight, 0, 270, 135);
  if (step?.armBoth === true) out.armBoth = true;
  return out;
};

const isNeutralStep = step => Math.abs(+step?.left || 0) < .01 && Math.abs(+step?.right || 0) < .01 && (step?.arm == null ? 135 : +step.arm) === 135 && (step?.armRight == null ? 135 : +step.armRight) === 135;

function movementKey(value) {
  return String(value || "").toLowerCase().trim().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 48);
}

// Compose only known, bounded skills. The model chooses the ingredients; this
// local layer owns duration, motor limits, obstacle metadata, and the final
// neutral pose. This keeps XEMO expressive without letting a thought create an
// unbounded motor program.
export function composeMovement(name, parts, options = {}) {
  const key = movementKey(name), list = Array.isArray(parts) ? parts : [ parts ];
  const maxParts = Math.max(1, Math.min(6, Number(options.maxParts) || 4));
  const maxSteps = Math.max(2, Math.min(18, Number(options.maxSteps) || 14));
  const maxMs = Math.max(800, Math.min(8e3, Number(options.maxMs) || 6e3));
  if (!key || key === "stop" || !list.length || list.length > maxParts) throw Error("invalid movement composition");
  const steps = [], labels = [], seen = new Set;
  let navigation = false, surface = "any";
  for (const part of list) {
    const partKey = movementKey(part);
    if (!partKey || seen.has(partKey) && partKey === key) throw Error("recursive movement composition");
    const movement = MOVEMENTS[partKey];
    if (!movement || !Array.isArray(movement.steps) || !movement.steps.length) throw Error("unknown movement ingredient: " + partKey);
    seen.add(partKey);
    labels.push(movement.label || partKey.replace(/_/g, " "));
    navigation ||= !!movement.navigation;
    if (movement.surface === "floor") surface = "floor";
    const copied = movement.steps.map(copyStep);
    // Built-ins finish neutral so a standalone gesture is tidy. Remove that
    // boundary pause when composing, otherwise every ingredient adds dead air.
    if (steps.length && isNeutralStep(steps[steps.length - 1])) steps.pop();
    steps.push(...copied);
    if (steps.length > maxSteps) throw Error("movement composition is too long");
  }
  if (!steps.length) throw Error("empty movement composition");
  if (!isNeutralStep(steps[steps.length - 1])) steps.push({ left: 0, right: 0, arm: 135, armRight: 135, ms: 240 });
  const total = steps.reduce((sum, step) => sum + step.ms, 0);
  if (total > maxMs) throw Error("movement composition is too slow");
  const movement = {
    label: String(options.label || labels.join(" then ")).slice(0, 100),
    surface,
    navigation,
    steps
  };
  MOVEMENTS[key] = movement;
  return movement;
}

export function makeBodySequence(name, steps) {
  const key = movementKey(name);
  if (!key || key === "stop" || !Array.isArray(steps) || !steps.length || steps.length > 8) throw Error("invalid body sequence");
  const navigation = steps.some(step => Math.abs(Number(step?.wl ?? step?.wheelLeft) || 0) > .01 || Math.abs(Number(step?.wr ?? step?.wheelRight) || 0) > .01);
  const movement = {
    label: "thought body sequence",
    surface: navigation ? "floor" : "any",
    navigation,
        steps: steps.map(step => ({
      left: clamp(step?.wl ?? step?.wheelLeft, -1, 1, 0),
      right: clamp(step?.wr ?? step?.wheelRight, -1, 1, 0),
      arm: clamp(step?.l, 0, 270, 135),
      armRight: clamp(step?.r, 0, 270, 135),
      armBoth: false,
      ms: clamp(step?.ms, 120, 1600, 360)
    }))
  };
  MOVEMENTS[key] = movement;
  return movement;
}

export function movementCatalog() {
  const groups = {
    navigation: [ "forward_short", "backward_short", "pivot_left", "pivot_right", "arc_left", "arc_right", "cautious_scan" ],
    social: [ "wave", "wave_right", "hello_big", "hug", "beckon", "high_five", "tiny_bow" ],
    expressive: [ "sway", "wiggle", "dance", "celebrate", "victory", "shy_peek", "curious_peek" ],
    arms: [ "arms_up", "arms_down", "point_left", "point_right", "alternating_raise", "mirror_sweep" ]
  };
  return Object.entries(groups).map(([group, names]) => `${group}: ${names.filter(name => MOVEMENTS[name]).join(", ")}`).join("; ");
}
