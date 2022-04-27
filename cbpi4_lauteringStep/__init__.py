from aiohttp import web
import asyncio
from cbpi.api import parameters, Property, action
from cbpi.api.step import StepResult, CBPiStep
from cbpi.api.timer import Timer
from datetime import datetime
import time
from voluptuous.schema_builder import message
from cbpi.api.dataclasses import NotificationAction, NotificationType
from cbpi.api.dataclasses import Kettle, Props
from cbpi.api import *
import logging
from socket import timeout
from typing import KeysView
from cbpi.api.config import ConfigType
from cbpi.api.base import CBPiBase
import warnings

logger = logging.getLogger(__name__)


@parameters([Property.Number(label="Lautering_Pause", description="Pause in minutes to wait for start lautering", configurable=True), 
             Property.Number(label="Heating_Delay", description="Delay in minutes to wait after start lautering for start heating", configurable=True), 
             Property.Number(label="Fly_Sparging_Delay", description="Delay in Minutes to wait after heating to start fly sparging", configurable=True), 
             Property.Number(label="Temp",description="Temperature to hold the wort to until lautering is completed", configurable=True),
             Property.Actor(label="Actor",description="Actor for fly sparging pump (should be a TimedActor with properties: direct_start == true and switch-off-delay)"),
             Property.Kettle(label="Kettle")])
class LauteringStep(CBPiStep):

    @action("Add 5 Minutes to Timer", [])
    async def add_timer(self):
        if self.timer.is_running == True:
            self.cbpi.notify(self.name, '5 Minutes added', NotificationType.INFO)
            await self.timer.add(300)
        else:
            self.cbpi.notify(self.name, 'Timer must be running to add time', NotificationType.WARNING)

    async def end_of_step(self):
        self.summary = ""
        self.kettle.target_temp = 0
        await self.setAutoMode(False)
        self.cbpi.notify(self.name, 'Step finished', NotificationType.SUCCESS)
        await asyncio.sleep(3)
       
        await self.next()

    async def buffer(self):
        await asyncio.sleep(1)
        await self.start_fly_sparging(0)

    async def start_fly_sparging(self,timer):
        if self.stopped is not True:
            self.summary = "sparging water: " + str(self.sparging_water) + " liter"
            self.cbpi.notify("Fly sparging", "sparging water: " + str(self.sparging_water) + " liter", NotificationType.INFO, action=[NotificationAction("Next Step", self.end_of_step),NotificationAction("add 1 liter", self.buffer)])
            
            if self.Actor is not None:
                if self.get_actor_state(self.Actor) is not True:
                    await self.actor_on(self.Actor)
                else:
                    self.remaining_water += 1
            await self.push_update()
            self.sparging_water += 1
        else:
            await self.push_update()

    async def start_heating(self,timer):
        if self.stopped is not True:
            self.summary = "Start heating"
            await self.set_target_temp(self.props.get("Kettle", None), int(self.props.get("Temp", None)))
            self.cbpi.notify(self.name, 'Heating started.', NotificationType.INFO)
            self.timer = Timer(int(self.props.get("Fly_Sparging_Delay",0)) *60 ,on_update=self.on_heating_update, on_done=self.start_fly_sparging)
            self.timer.start()
            self.timer.is_running = True
        await self.push_update()

    async def start_lautering(self,timer):
        if self.stopped is not True:
            self.summary = "Start lautering"
            self.cbpi.notify(self.name, 'Now start lautering!', NotificationType.INFO)
            await self.push_update()
            self.timer = Timer(int(self.props.get("Heating_Delay",0)) *60 ,on_update=self.on_lautering_update, on_done=self.start_heating)
            self.timer.start()
            self.timer.is_running = True
        await self.push_update()
       
    async def lautering_pause(self):
        if self.cbpi.kettle is not None and self.timer is None:
            self.timer = Timer(int(self.props.get("Lautering_Pause",0)) *60 ,on_update=self.on_pause_update, on_done=self.start_lautering)
            self.timer.start()
            self.timer.is_running = True
        elif self.cbpi.kettle is not None:
            self.timer.start()
            self.timer.is_running = True

        await self.push_update()

    async def on_pause_update(self,timer, seconds):
        self.summary = "lautering pause: " + Timer.format_time(seconds)
        await self.push_update()

    async def on_lautering_update(self,timer, seconds):
        self.summary = "start heating in: " + Timer.format_time(seconds)
        await self.push_update()

    async def on_heating_update(self,timer, seconds):
        self.summary = "start fly sparging in: " + Timer.format_time(seconds)
        await self.push_update()

    async def on_start(self):
        self.actor = self.cbpi.config.get("lautering_actor", None)
        if self.actor is None:
            logger.info("INIT Actor for lautering")
            try:
                await self.cbpi.config.add("lautering_actor", "", ConfigType.ACTOR, "Actor for lautering")
            except:
                logger.warning('Unable to update config')
        self.sparging_water=1
        self.remaining_water=0
        self.Actor=self.props.get("Actor", None)
        self.kettle=self.get_kettle(self.props.get("Kettle", None))
        if self.kettle is not None:
            self.kettle.target_temp = 0
        await self.setAutoMode(True)
        await asyncio.sleep(3)
        self.cbpi.notify("Transfer mash into lauter tun", "Transfer the mash into the lauter tun. If you ready click 'start lautering pause'", NotificationType.INFO, action=[NotificationAction("start lautering pause", self.lautering_pause)])
        self.stopped = False
        await self.push_update()

    async def on_stop(self):
        await self.timer.stop()
        self.stopped = True
        self.summary = ""
        await self.setAutoMode(False)
        await self.push_update()

    async def reset(self):
        self.timer = Timer(int(self.props.get("Lautering_Pause",0)) *60 ,on_update=self.on_pause_update, on_done=self.start_lautering)

    async def run(self):
        while self.running == True:
            if self.Actor is not None:
                if self.get_actor_state(self.Actor) is not True and self.remaining_water > 0:
                    await self.actor_on(self.Actor)
                    self.remaining_water -= 1
            
            await asyncio.sleep(1)
        return StepResult.DONE

    async def setAutoMode(self, auto_state):
        try:
            if (self.kettle.instance is None or self.kettle.instance.state == False) and (auto_state is True):
                await self.cbpi.kettle.toggle(self.kettle.id)
            elif (self.kettle.instance.state == True) and (auto_state is False):
                await self.cbpi.kettle.stop(self.kettle.id)
            await self.push_update()

        except Exception as e:
            logging.error("Failed to switch on KettleLogic {} {}".format(self.kettle.id, e))


def setup(cbpi):
    cbpi.plugin.register("LauteringStep", LauteringStep)
