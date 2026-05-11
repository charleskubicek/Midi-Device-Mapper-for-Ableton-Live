Remove the deivce_family_intents option completley, including all references to 'family' in the codesbase. rename variables if you need to.

instead the app will support the custom parameter system by using the format in custom_device_mappings.json.

this can be any file passed in in the template file.

if no file is passed in use the parameters as they appear in the device.

Remember all this only applies when the mapping file has a mapping of `type: device`

the mapping looks like this:

                mappings:
                    encoders:
                        range: row-1:1-8
                        slots: 1-8
                    buttons:
                        range: row-3:5-8
                        slots: 1-8

in this example the row is mapped to a 'slot', where slot relates to the family concept. the new name needs to be decided. It could be 'parameters', but in this case it won't be actual parameter numbers as they appear on a deivce, but instead the numbers are used by the device-mapping system to map dependent on the method chosen (blue-hand or custom)

another complexity is that we wantto allow paging, so actually, the encoder row will have more parameters mapped.

and there's the case of buttons. we need to express that 4 buttons will be mapped, bug again they can be paged. it could be that 'slot' is actually a good name.

there will need to be a new mapping type, 'parameter-pager', which the user can assign to a button/encoder