
Recently we've seen the need to have a shared folder for the functions.py file and related files that it imports. We need to find a place for this and ensure it gets deployed along with the generated script.

so we need a small repository of extentsions a user can refer to, or import. does it mean we need to copy our extension repo over to ableton too? think of some option.


ec4_client.py needs it's own module.


- Move all off the OSC sending stuff out of main_component, eg `OSCMultiClient` and it's usage, into some other module, right now it's in `main_component`


how should 'remote_on' in config work? it seems like our wireprotocol/HUD is the kind of way we want to publish outputs to other things. Or is it? How would a control surface configuration describe a module and a type of hook it binds into? Currently, the only hook we care about is publishing outputs. 