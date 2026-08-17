// XEMO's reusable body vocabulary. Values are deliberately conservative and
// expressed in the relay's normalized wheel range (-1..1) plus arm degrees.
export const MOVEMENTS={
  forward_short:{label:"careful short advance",surface:"floor",navigation:true,steps:[
    {left:.24,right:.24,arm:90,ms:600}]},
  forward_medium:{label:"steady short advance",surface:"floor",navigation:true,steps:[
    {left:.25,right:.25,arm:90,ms:1150}]},
  backward_short:{label:"careful short retreat",surface:"floor",navigation:true,steps:[
    {left:-.24,right:-.24,arm:90,ms:600}]},
  pivot_left:{label:"small pivot left",surface:"floor",navigation:true,steps:[
    {left:-.38,right:.38,arm:90,ms:520}]},
  pivot_right:{label:"small pivot right",surface:"floor",navigation:true,steps:[
    {left:.38,right:-.38,arm:90,ms:520}]},
  arc_left:{label:"curved path left",surface:"floor",navigation:true,steps:[
    {left:.14,right:.34,arm:90,ms:700}]},
  arc_right:{label:"curved path right",surface:"floor",navigation:true,steps:[
    {left:.34,right:.14,arm:90,ms:700}]},
  scan_left:{label:"look around left",surface:"floor",navigation:true,steps:[
    {left:-.3,right:.3,arm:90,ms:720}]},
  scan_right:{label:"look around right",surface:"floor",navigation:true,steps:[
    {left:.3,right:-.3,arm:90,ms:720}]},
  stop:{label:"full stop",surface:"any",navigation:true,steps:[
    {left:0,right:0,arm:90,ms:120}]},
  wave:{label:"friendly wave",surface:"any",steps:[
    {left:0,right:0,arm:55,ms:420},{left:0,right:0,arm:125,ms:420},
    {left:0,right:0,arm:55,ms:420},{left:0,right:0,arm:90,ms:360}]},
  arm_flap:{label:"happy arm flap",surface:"any",steps:[
    {left:0,right:0,arm:25,ms:360},{left:0,right:0,arm:145,ms:360},
    {left:0,right:0,arm:35,ms:360},{left:0,right:0,arm:135,ms:360},
    {left:0,right:0,arm:90,ms:360}]},
  dance:{label:"playful dance",surface:"floor",steps:[
    {left:.48,right:-.48,arm:45,ms:480},{left:-.48,right:.48,arm:135,ms:480},
    {left:.48,right:-.48,arm:55,ms:480},{left:0,right:0,arm:90,ms:420}]},
  wiggle:{label:"small wiggle",surface:"floor",steps:[
    {left:.42,right:-.42,arm:75,ms:360},{left:-.42,right:.42,arm:105,ms:360},
    {left:.42,right:-.42,arm:75,ms:360},{left:0,right:0,arm:90,ms:360}]},
  celebrate:{label:"celebration",surface:"floor",steps:[
    {left:.5,right:-.5,arm:135,ms:420},{left:-.5,right:.5,arm:45,ms:420},
    {left:0,right:0,arm:120,ms:360},{left:0,right:0,arm:90,ms:360}]},
  sway:{label:"gentle sway",surface:"floor",steps:[
    {left:.34,right:-.34,arm:70,ms:520},{left:-.34,right:.34,arm:110,ms:520},
    {left:0,right:0,arm:90,ms:400}]},
  left_wheel_twice:{label:"left wheel twice",surface:"floor",steps:[
    {left:.48,right:0,arm:90,ms:520},{left:0,right:0,arm:90,ms:260},
    {left:.48,right:0,arm:90,ms:520},{left:0,right:0,arm:90,ms:260}]},
  right_wheel_twice:{label:"right wheel twice",surface:"floor",steps:[
    {left:0,right:.48,arm:90,ms:520},{left:0,right:0,arm:90,ms:260},
    {left:0,right:.48,arm:90,ms:520},{left:0,right:0,arm:90,ms:260}]}
  ,tiny_bow:{label:"tiny bow",surface:"any",steps:[
    {left:0,right:0,arm:65,ms:360},{left:0,right:0,arm:115,ms:360},
    {left:0,right:0,arm:90,ms:360}]}
  ,shy_peek:{label:"shy peek",surface:"floor",steps:[
    {left:-.28,right:-.28,arm:55,ms:360},{left:.28,right:.28,arm:125,ms:360},
    {left:0,right:0,arm:90,ms:360}]}
  ,look_around:{label:"look around",surface:"floor",steps:[
    {left:.38,right:-.38,arm:90,ms:420},{left:-.38,right:.38,arm:90,ms:420},
    {left:0,right:0,arm:90,ms:300}]}
  ,curious_peek:{label:"curious peek",surface:"floor",steps:[
    {left:.24,right:.24,arm:70,ms:360},{left:-.24,right:-.24,arm:110,ms:360},
    {left:0,right:0,arm:90,ms:360}]}
  ,retreat_gently:{label:"gentle retreat",surface:"floor",steps:[
    {left:-.24,right:-.24,arm:90,ms:520},{left:0,right:0,arm:90,ms:260}]}
};
