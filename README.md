# cbpi4_lauteringStep

This step plugin is for the lauteringprocess, if you use fly sparging with a pump or magnet-valve directly connected to a water pipe.

The step will be configured with 3 timers. These timers will start one after another.

The first timer will start dirctly after you comfirm, that you transfer the mash from the mash tun to the lautering tun. 
This time is to let the grain sink to the ground before you start lautering.
If the first timer is completed, you can open the valve to start lautering.

Then the second timer starts. If this timer is completed the target-temp of the boil-kettle is set to a defined temp, so that the wort will not cool down.

After setting the target-temp the third timer starts. This time is a delay for starting with fly sparging.
If the third timer is completed, a notification will be shown, which counts how often you activates the timedActor of the pump or valve for fly sparging.
(You can stop the time the pump needs to fill a cup of 1 liter or 1 gallon and use this time at the timedActor.)

The notification has 2 actions. 
The first one is to activate the actor another amount of time. 
If the actor is currently active, the actions will be counted and the actor will activated again if the amount of time is reached.
This will repeated as long as the lautering step is active and the remain-action-counter is not 0.
The other action got you to the next brewstep.

ToDo:
- [ ] add optional second actor for lautering valve which opens after the first timer is reached.