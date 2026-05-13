# Live API 12.4.0

> This is unofficial documentation. Please do not contact Ableton with questions or problems relating to the use of this documentation.


# Live


## Live.Application

- **Live.Application.combine_apcs()** _Built-In_
  > combine_apcs() -> bool : Returns true if multiple APCs should be combined. C++ signature :  bool combine_apcs()
- **Live.Application.encrypt_challenge()** _Built-In_
  > encrypt_challenge( (int)dongle1, (int)dongle2 [, (int)key_index=0]) -> tuple : Returns an encrypted challenge based on the TEA algortithm C++ signature :  boost::python::tuple encrypt_challenge(int,int [,int=0])
- **Live.Application.encrypt_challenge2()** _Built-In_
  > encrypt_challenge2( (int)arg1) -> int : Returns the UMAC hash for the given challenge. C++ signature :  int encrypt_challenge2(int)
- **Live.Application.get_application()** _Built-In_
  > get_application() -> Application : Returns the application instance. C++ signature :  TWeakPtr<TPyHandle<ASongApp>> get_application()
- **Live.Application.get_random_int()** _Built-In_
  > get_random_int( (int)arg1, (int)arg2) -> int : Returns a random integer from the given range. C++ signature :  int get_random_int(int,int)

### Live.Application.Application

> This class represents the Live application.

- **Live.Application.Application.get_bugfix_version()** _Built-In_
  > get_bugfix_version( (Application)arg1) -> int : Returns an integer representing the bugfix version of Live. C++ signature :  int get_bugfix_version(TPyHandle<ASongApp>)
- **Live.Application.Application.get_build_id()** _Built-In_
  > get_build_id( (Application)arg1) -> str : Returns a string identifying the build. C++ signature :  TString get_build_id(TPyHandle<ASongApp>)
- **Live.Application.Application.get_document()** _Built-In_
  > get_document( (Application)arg1) -> Song : Returns the current Live Set. C++ signature :  TWeakPtr<TPyHandle<ASong>> get_document(TPyHandle<ASongApp>)
- **Live.Application.Application.get_major_version()** _Built-In_
  > get_major_version( (Application)arg1) -> int : Returns an integer representing the major version of Live. C++ signature :  int get_major_version(TPyHandle<ASongApp>)
- **Live.Application.Application.get_minor_version()** _Built-In_
  > get_minor_version( (Application)arg1) -> int : Returns an integer representing the minor version of Live. C++ signature :  int get_minor_version(TPyHandle<ASongApp>)
- **Live.Application.Application.get_variant()** _Built-In_
  > get_variant( (Application)arg1) -> str : Returns one of the strings in Live.Application.Variants. C++ signature :  TString get_variant(TPyHandle<ASongApp>)
- **Live.Application.Application.get_version_string()** _Built-In_
  > get_version_string( (Application)arg1) -> str : Returns the full version string of Live. C++ signature :  TString get_version_string(TPyHandle<ASongApp>)
- **Live.Application.Application.has_option()** _Built-In_
  > has_option( (Application)arg1, (object)arg2) -> bool : Returns True if the given entry exists in Options.txt, False otherwise. C++ signature :  bool has_option(TPyHandle<ASongApp>,TString)
- **Live.Application.Application.press_current_dialog_button()** _Built-In_
  > press_current_dialog_button( (Application)arg1, (int)arg2) -> None : Press a button, by index, on the current message box. C++ signature :  void press_current_dialog_button(TPyHandle<ASongApp>,int)
- **Live.Application.Application.show_message()** _Built-In_
  > show_message( (Application)arg1, (Text)text [, (int)buttons=Application.MessageButtons.OK_BUTTON [, (bool)enable_markup=False [, (bool)show_success_icon=False]]]) -> int : Shows a message box, returning the position of the pressed button. C++ signature :  int show_message(TPyHandle<ASongApp>,TText [,int=Application.MessageButtons.OK_BUTTON [,bool=False [,bool=False]]])
- **Live.Application.Application.show_on_the_fly_message()** _Built-In_
  > show_on_the_fly_message( (Application)arg1, (str)message [, (int)buttons=Application.MessageButtons.OK_BUTTON [, (bool)enable_markup=False [, (bool)show_success_icon=False [, (int)push_dialog_type=Application.PushDialogType.MESSAGE_BOX]]]]) -> int : Same as show_message, but for when there is no predefined Text object. C++ signature :  int show_on_the_fly_message(TPyHandle<ASongApp>,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>> [,int=Application.MessageButtons.OK_BUTTON [,bool=False [,bool=False [,int=Application.PushDialogType.MESSAGE_BOX]]]])
- **Live.Application.Application.average_process_usage** _Property_RO_ — `get, observe`
  > Reports Live's average CPU load.
- **Live.Application.Application.browser** _Property_RO_ — `get`
  > Returns an interface to the browser.
- **Live.Application.Application.canonical_parent** _Property_RO_ — `get`
  > Returns the canonical parent of the application.
- **Live.Application.Application.control_surfaces** _Property_RO_ — `get, observe`
  > Const access to a list of the control surfaces selected in preferences, in the same order.The list contains None if no control surface is active at that index.
- **Live.Application.Application.current_dialog_button_count** _Property_RO_ — `get`
  > Number of buttons on the current dialog.
- **Live.Application.Application.current_dialog_message** _Property_RO_ — `get`
  > Text of the last dialog that appeared; Empty if all dialogs just disappeared.
- **Live.Application.Application.number_of_push_apps_running** _Property_RO_ — `get`
  > Returns the number of connected Push apps.
- **Live.Application.Application.open_dialog_count** _Property_RO_ — `get, observe`
  > The number of open dialogs in Live. 0 if not dialog is open.
- **Live.Application.Application.peak_process_usage** _Property_RO_ — `get, observe`
  > Reports Live's peak CPU load.
- **Live.Application.Application.unavailable_features** _Property_RO_ — `get, observe`
  > List of features that are unavailable due to limitations of the current Live edition.
- **Live.Application.Application.view** _Property_RO_ — `get`
  > Returns the applications view component.

#### Live.Application.Application.View

> This class represents the view aspects of the Live application.

- **Live.Application.Application.View.available_main_views()** _Built-In_
  > available_main_views( (View)arg1) -> StringVector : Return a list of strings with the available subcomponent views, which is to be specified, when using the rest of this classes functions. A 'subcomponent view' is a main view component of a document view, like the Session view, the Arranger or Detailview and so on... C++ signature :  std::__1::vector<TString, std::__1::allocator<TString>> available_main_views(TPyViewData<ASongApp>)
- **Live.Application.Application.View.focus_view()** _Built-In_
  > focus_view( (View)arg1, (object)arg2) -> None : Show and focus one through the identifier string specified view. C++ signature :  void focus_view(TPyViewData<ASongApp>,TString)
- **Live.Application.Application.View.hide_view()** _Built-In_
  > hide_view( (View)arg1, (object)arg2) -> None : Hide one through the identifier string specified view. C++ signature :  void hide_view(TPyViewData<ASongApp>,TString)
- **Live.Application.Application.View.is_view_visible()** _Built-In_
  > is_view_visible( (View)arg1, (object)identifier [, (bool)main_window_only=True]) -> bool : Return true if the through the identifier string specified view is currently visible. If main_window_only is set to False, this will also check in second window. Notifications from the second window are not yet supported. C++ signature :  bool is_view_visible(TPyViewData<ASongApp>,TString [,bool=True])
- **Live.Application.Application.View.scroll_view()** _Built-In_
  > scroll_view( (View)arg1, (int)arg2, (object)arg3, (bool)arg4) -> None : Scroll through the identifier string specified view into the given direction, if possible.  Will silently return if the specified view can not perform the requested action. C++ signature :  void scroll_view(TPyViewData<ASongApp>,int,TString,bool)
- **Live.Application.Application.View.show_view()** _Built-In_
  > show_view( (View)arg1, (object)arg2) -> None : Show one through the identifier string specified view. Will throw a runtime error if this is called in Live's initialization scope. C++ signature :  void show_view(TPyViewData<ASongApp>,TString)
- **Live.Application.Application.View.toggle_browse()** _Built-In_
  > toggle_browse( (View)arg1) -> None : Reveals the device chain, the browser and starts hot swap for the selected device. Calling this function again stops hot swap. C++ signature :  void toggle_browse(TPyViewData<ASongApp>)
- **Live.Application.Application.View.zoom_view()** _Built-In_
  > zoom_view( (View)arg1, (int)arg2, (object)arg3, (bool)arg4) -> None : Zoom through the identifier string specified view into the given direction, if possible.  Will silently return if the specified view can not perform the requested action. C++ signature :  void zoom_view(TPyViewData<ASongApp>,int,TString,bool)
- **Live.Application.Application.View.browse_mode** _Property_RO_ — `get, observe`
  > Return true if HotSwap mode is active for any target.
- **Live.Application.Application.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the application view.
- **Live.Application.Application.View.focused_document_view** _Property_RO_ — `get, observe`
  > Return the name of the document view ('Session' or 'Arranger')shown in the currently selected window.

##### Live.Application.Application.View.NavDirection

  - Enum (4): `up=up`, `down=down`, `left=left`, `right=right`

### Live.Application.ControlDescription

> Describes a control present in a control surface proxy

- **Live.Application.ControlDescription.id** _Property_RO_ — `get`
- **Live.Application.ControlDescription.name** _Property_RO_ — `get`

### Live.Application.ControlDescriptionVector

> A container for returning control descriptions.

- **Live.Application.ControlDescriptionVector.append()** _Built-In_
  > append( (ControlDescriptionVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<TControlDescription, std::__1::allocator<TControlDescription>> {lvalue},boost::python::api::object)
- **Live.Application.ControlDescriptionVector.extend()** _Built-In_
  > extend( (ControlDescriptionVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<TControlDescription, std::__1::allocator<TControlDescription>> {lvalue},boost::python::api::object)

### Live.Application.ControlSurfaceProxy

> Represents a control surface running in a different process. For use by M4L

- **Live.Application.ControlSurfaceProxy.enable_receive_midi()** _Built-In_
  > enable_receive_midi( (ControlSurfaceProxy)arg1, (bool)arg2) -> None : C++ signature :  void enable_receive_midi(APythonControlSurfaceProxy {lvalue},bool)
- **Live.Application.ControlSurfaceProxy.fetch_received_midi_messages()** _Built-In_
  > fetch_received_midi_messages( (ControlSurfaceProxy)arg1) -> tuple : C++ signature :  boost::python::tuple fetch_received_midi_messages(APythonControlSurfaceProxy {lvalue})
- **Live.Application.ControlSurfaceProxy.fetch_received_values()** _Built-In_
  > fetch_received_values( (ControlSurfaceProxy)arg1) -> tuple : C++ signature :  boost::python::tuple fetch_received_values(APythonControlSurfaceProxy {lvalue})
- **Live.Application.ControlSurfaceProxy.grab_control()** _Built-In_
  > grab_control( (ControlSurfaceProxy)arg1, (int)arg2) -> None : C++ signature :  void grab_control(APythonControlSurfaceProxy {lvalue},int)
- **Live.Application.ControlSurfaceProxy.release_control()** _Built-In_
  > release_control( (ControlSurfaceProxy)arg1, (int)arg2) -> None : C++ signature :  void release_control(APythonControlSurfaceProxy {lvalue},int)
- **Live.Application.ControlSurfaceProxy.send_midi()** _Built-In_
  > send_midi( (ControlSurfaceProxy)arg1, (tuple)arg2) -> None : C++ signature :  void send_midi(APythonControlSurfaceProxy {lvalue},boost::python::tuple)
- **Live.Application.ControlSurfaceProxy.send_value()** _Built-In_
  > send_value( (ControlSurfaceProxy)arg1, (tuple)arg2) -> None : C++ signature :  void send_value(APythonControlSurfaceProxy {lvalue},boost::python::tuple)
- **Live.Application.ControlSurfaceProxy.subscribe_to_control()** _Built-In_
  > subscribe_to_control( (ControlSurfaceProxy)arg1, (int)arg2) -> None : C++ signature :  void subscribe_to_control(APythonControlSurfaceProxy {lvalue},int)
- **Live.Application.ControlSurfaceProxy.unsubscribe_from_control()** _Built-In_
  > unsubscribe_from_control( (ControlSurfaceProxy)arg1, (int)arg2) -> None : C++ signature :  void unsubscribe_from_control(APythonControlSurfaceProxy {lvalue},int)
- **Live.Application.ControlSurfaceProxy.control_descriptions** _Property_RO_ — `get`
- **Live.Application.ControlSurfaceProxy.pad_layout** _Property_RO_ — `get, observe`
  > The layout of pads on Push.
- **Live.Application.ControlSurfaceProxy.type_name** _Property_RO_ — `get`

### Live.Application.MessageButtons

> Specifies the characteristics of the message box, e.g. which buttons to show.

  - Enum (6): `OK_BUTTON=OK_BUTTON`, `OK_NEW_SET_BUTTON=OK_NEW_SET_BUTTON`, `OK_RETRY_BUTTON=OK_RETRY_BUTTON`, `SAVE_DONT_SAVE_BUTTON=SAVE_DONT_SAVE_BUTTON`, `OK_ACCOUNT_BUTTON=OK_ACCOUNT_BUTTON`, `OK_PURCHASE_BUTTON=OK_PURCHASE_BUTTON`

### Live.Application.PushDialogType

> Specifies the dialog type for Push.

  - Enum (3): `MESSAGE_BOX=MESSAGE_BOX`, `OUT_OF_UNLOCKS_DIALOG=OUT_OF_UNLOCKS_DIALOG`, `RENT_TO_OWN_LICENSE_EXPIRED_DIALOG=RENT_TO_OWN_LICENSE_EXPIRED_DIALOG`

### Live.Application.UnavailableFeature

  - Enum (1): `note_velocity_ranges_and_probabilities=note_velocity_ranges_and_probabilities`

### Live.Application.UnavailableFeatureVector

> A container for returning unavailable features.

- **Live.Application.UnavailableFeatureVector.append()** _Built-In_
  > append( (UnavailableFeatureVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<NPythonApplication::TUnavailableFeature, std::__1::allocator<NPythonApplication::TUnavailableFeature>> {lvalue},boost::python::api::object)
- **Live.Application.UnavailableFeatureVector.extend()** _Built-In_
  > extend( (UnavailableFeatureVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<NPythonApplication::TUnavailableFeature, std::__1::allocator<NPythonApplication::TUnavailableFeature>> {lvalue},boost::python::api::object)

### Live.Application.Variants

> Holds strings representing what type of Live is running.

- **Live.Application.Variants.BETA** _Value_
  > str(object='') -> strstr(bytes_or_buffer[, encoding[, errors]]) -> strCreate a new string object from the given object. If encoding orerrors is specified, then the object must expose a data bufferthat will be decoded using the given encoding and error handler.Otherwise, returns the result of object.__str__() (if defined)or repr(object).encoding defaults to sys.getdefaultencoding().errors defaults to 'strict'.
- **Live.Application.Variants.INTRO** _Value_
  > str(object='') -> strstr(bytes_or_buffer[, encoding[, errors]]) -> strCreate a new string object from the given object. If encoding orerrors is specified, then the object must expose a data bufferthat will be decoded using the given encoding and error handler.Otherwise, returns the result of object.__str__() (if defined)or repr(object).encoding defaults to sys.getdefaultencoding().errors defaults to 'strict'.
- **Live.Application.Variants.LITE** _Value_
  > str(object='') -> strstr(bytes_or_buffer[, encoding[, errors]]) -> strCreate a new string object from the given object. If encoding orerrors is specified, then the object must expose a data bufferthat will be decoded using the given encoding and error handler.Otherwise, returns the result of object.__str__() (if defined)or repr(object).encoding defaults to sys.getdefaultencoding().errors defaults to 'strict'.
- **Live.Application.Variants.STANDARD** _Value_
  > str(object='') -> strstr(bytes_or_buffer[, encoding[, errors]]) -> strCreate a new string object from the given object. If encoding orerrors is specified, then the object must expose a data bufferthat will be decoded using the given encoding and error handler.Otherwise, returns the result of object.__str__() (if defined)or repr(object).encoding defaults to sys.getdefaultencoding().errors defaults to 'strict'.
- **Live.Application.Variants.SUITE** _Value_
  > str(object='') -> strstr(bytes_or_buffer[, encoding[, errors]]) -> strCreate a new string object from the given object. If encoding orerrors is specified, then the object must expose a data bufferthat will be decoded using the given encoding and error handler.Otherwise, returns the result of object.__str__() (if defined)or repr(object).encoding defaults to sys.getdefaultencoding().errors defaults to 'strict'.
- **Live.Application.Variants.TRIAL** _Value_
  > str(object='') -> strstr(bytes_or_buffer[, encoding[, errors]]) -> strCreate a new string object from the given object. If encoding orerrors is specified, then the object must expose a data bufferthat will be decoded using the given encoding and error handler.Otherwise, returns the result of object.__str__() (if defined)or repr(object).encoding defaults to sys.getdefaultencoding().errors defaults to 'strict'.

## Live.Base

- **Live.Base.get_text()** _Built-In_
  > get_text( (str)classname, (str)textname) -> Text : Retrieves the (translated) Text identified by `classname` and `textname`. C++ signature :  TText const* get_text(std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>)
- **Live.Base.log()** _Built-In_
  > log( (str)arg1) -> None : C++ signature :  void log(std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>)
- **Live.Base.subst_args()** _Built-In_
  > subst_args( (Text)text [, (str)arg1='' [, (str)arg2='' [, (str)arg3='' [, (str)arg4='' [, (str)arg5='']]]]]) -> str : C++ signature :  std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>> subst_args(TText [,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>='' [,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>='' [,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>='' [,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>='' [,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>='']]]]])

### Live.Base.FloatVector

> A simple container for returning floats from Live.

- **Live.Base.FloatVector.append()** _Built-In_
  > append( (FloatVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<float, std::__1::allocator<float>> {lvalue},boost::python::api::object)
- **Live.Base.FloatVector.extend()** _Built-In_
  > extend( (FloatVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<float, std::__1::allocator<float>> {lvalue},boost::python::api::object)

### Live.Base.IntU64Vector

> A simple container for returning unsigned long integers from Live.

- **Live.Base.IntU64Vector.append()** _Built-In_
  > append( (IntU64Vector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<unsigned long long, std::__1::allocator<unsigned long long>> {lvalue},boost::python::api::object)
- **Live.Base.IntU64Vector.extend()** _Built-In_
  > extend( (IntU64Vector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<unsigned long long, std::__1::allocator<unsigned long long>> {lvalue},boost::python::api::object)

### Live.Base.IntVector

> A simple container for returning integers from Live.

- **Live.Base.IntVector.append()** _Built-In_
  > append( (IntVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<int, std::__1::allocator<int>> {lvalue},boost::python::api::object)
- **Live.Base.IntVector.extend()** _Built-In_
  > extend( (IntVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<int, std::__1::allocator<int>> {lvalue},boost::python::api::object)

### Live.Base.LimitationError

- **Live.Base.LimitationError.add_note** _Value_
  > Exception.add_note(note) -- add a note to the exception
- **Live.Base.LimitationError.args** _Value_
- **Live.Base.LimitationError.with_traceback** _Value_
  > Exception.with_traceback(tb) -- set self.__traceback__ to tb and return self.

### Live.Base.ObjectVector

> A simple read only container for returning python objects.

- **Live.Base.ObjectVector.append()** _Built-In_
  > append( (ObjectVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<boost::python::api::object, std::__1::allocator<boost::python::api::object>> {lvalue},boost::python::api::object)
- **Live.Base.ObjectVector.extend()** _Built-In_
  > extend( (ObjectVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<boost::python::api::object, std::__1::allocator<boost::python::api::object>> {lvalue},boost::python::api::object)

### Live.Base.StringVector

> A simple container for returning strings from Live.

- **Live.Base.StringVector.append()** _Built-In_
  > append( (StringVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<TString, std::__1::allocator<TString>> {lvalue},boost::python::api::object)
- **Live.Base.StringVector.extend()** _Built-In_
  > extend( (StringVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<TString, std::__1::allocator<TString>> {lvalue},boost::python::api::object)

### Live.Base.Text

> A translatable, immutable string.

- **Live.Base.Text.text** _Property_RO_ — `get`

### Live.Base.Timer

> A timer that will trigger a callback after a certain inverval. The timer can be repeated and will trigger the callback every interval. Errors in the callback will stop the timer.

- **Live.Base.Timer.restart()** _Built-In_
  > restart( (Timer)arg1) -> None : C++ signature :  void restart(PythonTimer {lvalue})
- **Live.Base.Timer.start()** _Built-In_
  > start( (Timer)arg1) -> None : C++ signature :  void start(PythonTimer {lvalue})
- **Live.Base.Timer.stop()** _Built-In_
  > stop( (Timer)arg1) -> None : C++ signature :  void stop(PythonTimer {lvalue})
- **Live.Base.Timer.running** _Property_RO_ — `get`

### Live.Base.Vector

> A simple read only container for returning objects from Live.

- **Live.Base.Vector.append()** _Built-In_
  > append( (Vector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<TWeakPtr<TPyHandleBase>, std::__1::allocator<TWeakPtr<TPyHandleBase>>> {lvalue},boost::python::api::object)
- **Live.Base.Vector.extend()** _Built-In_
  > extend( (Vector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<TWeakPtr<TPyHandleBase>, std::__1::allocator<TWeakPtr<TPyHandleBase>>> {lvalue},boost::python::api::object)

## Live.Browser


### Live.Browser.Browser

> This class represents the live browser data base.

- **Live.Browser.Browser.load_item()** _Built-In_
  > load_item( (Browser)arg1, (BrowserItem)arg2) -> None : Loads the provided browser item. C++ signature :  void load_item(TPyHandle<ABrowserDelegate>,NPythonBrowser::TPythonBrowserItem)
- **Live.Browser.Browser.preview_item()** _Built-In_
  > preview_item( (Browser)arg1, (BrowserItem)arg2) -> None : Previews the provided browser item. C++ signature :  void preview_item(TPyHandle<ABrowserDelegate>,NPythonBrowser::TPythonBrowserItem)
- **Live.Browser.Browser.relation_to_hotswap_target()** _Built-In_
  > relation_to_hotswap_target( (Browser)arg1, (BrowserItem)arg2) -> Relation : Returns the relation between the given browser item and the current hotswap target C++ signature :  ableton::live_library::Relation relation_to_hotswap_target(TPyHandle<ABrowserDelegate>,NPythonBrowser::TPythonBrowserItem)
- **Live.Browser.Browser.stop_preview()** _Built-In_
  > stop_preview( (Browser)arg1) -> None : Stop the current preview. C++ signature :  void stop_preview(TPyHandle<ABrowserDelegate>)
- **Live.Browser.Browser.audio_effects** _Property_RO_ — `get`
  > Returns a browser item with access to all the Audio Effects content.
- **Live.Browser.Browser.clips** _Property_RO_ — `get`
  > Returns a browser item with access to all the Clips content.
- **Live.Browser.Browser.colors** _Property_RO_ — `get`
  > Returns a list of browser items containing the configured colors.
- **Live.Browser.Browser.current_project** _Property_RO_ — `get`
  > Returns a browser item with access to all the Current Project content.
- **Live.Browser.Browser.drums** _Property_RO_ — `get`
  > Returns a browser item with access to all the Drums content.
- **Live.Browser.Browser.filter_type** _Property_ — `get, set, observe`
  > Bang triggered when the hotswap target has changed.
- **Live.Browser.Browser.hotswap_target** _Property_ — `get, set, observe`
  > Bang triggered when the hotswap target has changed.
- **Live.Browser.Browser.instruments** _Property_RO_ — `get`
  > Returns a browser item with access to all the Instruments content.
- **Live.Browser.Browser.legacy_libraries** _Property_RO_ — `get`
  > Returns a list of browser items containing the installed legacy libraries. The list is always empty as legacy library handling has been removed.
- **Live.Browser.Browser.max_for_live** _Property_RO_ — `get`
  > Returns a browser item with access to all the Max For Live content.
- **Live.Browser.Browser.midi_effects** _Property_RO_ — `get`
  > Returns a browser item with access to all the Midi Effects content.
- **Live.Browser.Browser.packs** _Property_RO_ — `get`
  > Returns a browser item with access to all the Packs content.
- **Live.Browser.Browser.plugins** _Property_RO_ — `get`
  > Returns a browser item with access to all the Plugins content.
- **Live.Browser.Browser.samples** _Property_RO_ — `get`
  > Returns a browser item with access to all the Samples content.
- **Live.Browser.Browser.sounds** _Property_RO_ — `get`
  > Returns a browser item with access to all the Sounds content.
- **Live.Browser.Browser.user_folders** _Property_RO_ — `get`
  > Returns a list of browser items containing all the user folders.
- **Live.Browser.Browser.user_library** _Property_RO_ — `get`
  > Returns a browser item with access to all the User Library content.

### Live.Browser.BrowserItem

> This class represents an item of the browser hierarchy.

- **Live.Browser.BrowserItem.children** _Property_RO_ — `get`
  > Const access to the descendants of this browser item.
- **Live.Browser.BrowserItem.is_device** _Property_RO_ — `get`
  > Indicates if the browser item represents a device.
- **Live.Browser.BrowserItem.is_folder** _Property_RO_ — `get`
  > Indicates if the browser item represents folder.
- **Live.Browser.BrowserItem.is_loadable** _Property_RO_ — `get`
  > True if item can be loaded via the Browser's 'load_item' method.
- **Live.Browser.BrowserItem.is_selected** _Property_RO_ — `get`
  > True if the item is ancestor of or the actual selection.
- **Live.Browser.BrowserItem.iter_children** _Property_RO_ — `get`
  > Const iterable access to the descendants of this browser item.
- **Live.Browser.BrowserItem.name** _Property_RO_ — `get`
  > Const access to the canonical display name of this browser item.
- **Live.Browser.BrowserItem.source** _Property_RO_ — `get`
  > Specifies where does item come from -- i.e. Live pack, user library...
- **Live.Browser.BrowserItem.uri** _Property_RO_ — `get`
  > The uri describes a unique identifier for a browser item.

### Live.Browser.BrowserItemIterator

> This class iterates over children of another BrowserItem.


### Live.Browser.BrowserItemVector

> A container for returning browser items from Live.

- **Live.Browser.BrowserItemVector.append()** _Built-In_
  > append( (BrowserItemVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<NPythonBrowser::TPythonBrowserItem, std::__1::allocator<NPythonBrowser::TPythonBrowserItem>> {lvalue},boost::python::api::object)
- **Live.Browser.BrowserItemVector.extend()** _Built-In_
  > extend( (BrowserItemVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<NPythonBrowser::TPythonBrowserItem, std::__1::allocator<NPythonBrowser::TPythonBrowserItem>> {lvalue},boost::python::api::object)

### Live.Browser.FilterType

  - Enum (9): `disabled=disabled`, `hotswap_off=hotswap_off`, `instrument_hotswap=instrument_hotswap`, `audio_effect_hotswap=audio_effect_hotswap`, `midi_effect_hotswap=midi_effect_hotswap`, `drum_pad_hotswap=drum_pad_hotswap`, `midi_track_devices=midi_track_devices`, `samples=samples`, `count=count`

### Live.Browser.Relation

  - Enum (4): `ancestor=ancestor`, `equal=equal`, `descendant=descendant`, `none=none`

## Live.CcControlDevice


### Live.CcControlDevice.CcControlDevice

> This class represents a CcControl device.

- **Live.CcControlDevice.CcControlDevice.resend()** _Built-In_
  > resend( (CcControlDevice)self) -> None : Resend all CC values. C++ signature :  void resend(TCcControlDevicePyHandle)
- **Live.CcControlDevice.CcControlDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.CcControlDevice.CcControlDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.CcControlDevice.CcControlDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.CcControlDevice.CcControlDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.CcControlDevice.CcControlDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.CcControlDevice.CcControlDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.CcControlDevice.CcControlDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.CcControlDevice.CcControlDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.CcControlDevice.CcControlDevice.custom_bool_target** _Property_ — `get, set, observe`
  > Return the custom bool target
- **Live.CcControlDevice.CcControlDevice.custom_bool_target_list** _Property_RO_ — `get`
  > Return the custom bool target list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_0** _Property_ — `get, set, observe`
  > Return the custom float target 0
- **Live.CcControlDevice.CcControlDevice.custom_float_target_0_list** _Property_RO_ — `get`
  > Return the custom float target 0 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_1** _Property_ — `get, set, observe`
  > Return the custom float target 1
- **Live.CcControlDevice.CcControlDevice.custom_float_target_10** _Property_ — `get, set, observe`
  > Return the custom float target 10
- **Live.CcControlDevice.CcControlDevice.custom_float_target_10_list** _Property_RO_ — `get`
  > Return the custom float target 10 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_11** _Property_ — `get, set, observe`
  > Return the custom float target 11
- **Live.CcControlDevice.CcControlDevice.custom_float_target_11_list** _Property_RO_ — `get`
  > Return the custom float target 11 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_1_list** _Property_RO_ — `get`
  > Return the custom float target 1 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_2** _Property_ — `get, set, observe`
  > Return the custom float target 2
- **Live.CcControlDevice.CcControlDevice.custom_float_target_2_list** _Property_RO_ — `get`
  > Return the custom float target 2 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_3** _Property_ — `get, set, observe`
  > Return the custom float target 3
- **Live.CcControlDevice.CcControlDevice.custom_float_target_3_list** _Property_RO_ — `get`
  > Return the custom float target 3 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_4** _Property_ — `get, set, observe`
  > Return the custom float target 4
- **Live.CcControlDevice.CcControlDevice.custom_float_target_4_list** _Property_RO_ — `get`
  > Return the custom float target 4 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_5** _Property_ — `get, set, observe`
  > Return the custom float target 5
- **Live.CcControlDevice.CcControlDevice.custom_float_target_5_list** _Property_RO_ — `get`
  > Return the custom float target 5 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_6** _Property_ — `get, set, observe`
  > Return the custom float target 6
- **Live.CcControlDevice.CcControlDevice.custom_float_target_6_list** _Property_RO_ — `get`
  > Return the custom float target 6 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_7** _Property_ — `get, set, observe`
  > Return the custom float target 7
- **Live.CcControlDevice.CcControlDevice.custom_float_target_7_list** _Property_RO_ — `get`
  > Return the custom float target 7 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_8** _Property_ — `get, set, observe`
  > Return the custom float target 8
- **Live.CcControlDevice.CcControlDevice.custom_float_target_8_list** _Property_RO_ — `get`
  > Return the custom float target 8 list
- **Live.CcControlDevice.CcControlDevice.custom_float_target_9** _Property_ — `get, set, observe`
  > Return the custom float target 9
- **Live.CcControlDevice.CcControlDevice.custom_float_target_9_list** _Property_RO_ — `get`
  > Return the custom float target 9 list
- **Live.CcControlDevice.CcControlDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.CcControlDevice.CcControlDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.CcControlDevice.CcControlDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.CcControlDevice.CcControlDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.CcControlDevice.CcControlDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.CcControlDevice.CcControlDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.CcControlDevice.CcControlDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.CcControlDevice.CcControlDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.CcControlDevice.CcControlDevice.View

> Representing the view aspects of a device.

- **Live.CcControlDevice.CcControlDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.CcControlDevice.CcControlDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.Chain


### Live.Chain.Chain

> This class represents a group device chain in Live.

- **Live.Chain.Chain.delete_device()** _Built-In_
  > delete_device( (Chain)arg1, (int)arg2) -> None : Remove a device identified by its index from the chain. Throws runtime error if bad index.  C++ signature :  void delete_device(TChainPyHandle,int)
- **Live.Chain.Chain.duplicate_device()** _Built-In_
  > duplicate_device( (Chain)arg1, (int)arg2) -> None : Duplicate the device at the given index in the chain. C++ signature :  void duplicate_device(TChainPyHandle,int)
- **Live.Chain.Chain.insert_device()** _Built-In_
  > insert_device( (Chain)arg1, (str)DeviceName [, (int)DeviceIndex=-1]) -> LomObject : Add a device at a given index in the chain. At end if -1. C++ signature :  TWeakPtr<TPyHandleBase> insert_device(TChainPyHandle,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>> [,int=-1])
- **Live.Chain.Chain.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the chain.
- **Live.Chain.Chain.color** _Property_ — `get, set, observe`
  > Access the color index of the Chain.
- **Live.Chain.Chain.color_index** _Property_ — `get, set, observe`
  > Access the color index of the Chain.
- **Live.Chain.Chain.devices** _Property_RO_ — `get, observe`
  > Return const access to all available Devices that are present in the chains
- **Live.Chain.Chain.has_audio_input** _Property_RO_ — `get`
  > return True, if this Chain can be feed with an Audio signal. This istrue for all Audio Chains.
- **Live.Chain.Chain.has_audio_output** _Property_RO_ — `get`
  > return True, if this Chain sends out an Audio signal. This istrue for all Audio Chains, and MIDI chains with an Instrument.
- **Live.Chain.Chain.has_midi_input** _Property_RO_ — `get`
  > return True, if this Chain can be feed with an Audio signal. This istrue for all MIDI Chains.
- **Live.Chain.Chain.has_midi_output** _Property_RO_ — `get`
  > return True, if this Chain sends out MIDI events. This istrue for all MIDI Chains with no Instruments.
- **Live.Chain.Chain.is_auto_colored** _Property_ — `get, set, observe`
  > Get/set access to the auto color flag of the Chain.If True, the Chain will always have the same color as the containingTrack or Chain.
- **Live.Chain.Chain.mixer_device** _Property_RO_ — `get`
  > Return access to the mixer device that holds the chain's mixer parameters:the Volume, Pan, and Sendamounts.
- **Live.Chain.Chain.mute** _Property_ — `get, set, observe`
  > Mute/unmute the chain.
- **Live.Chain.Chain.muted_via_solo** _Property_RO_ — `get, observe`
  > Return const access to whether this chain is muted due to some other chainbeing soloed.
- **Live.Chain.Chain.name** _Property_ — `get, set, observe`
  > Read/write access to the name of the Chain, as visible in the track header.
- **Live.Chain.Chain.solo** _Property_ — `get, set, observe`
  > Get/Set the solo status of the chain. Note that this will not disable thesolo state of any other Chain in the same rack. If you want exclusive solo, you have to disable the solo state of the other Chains manually.

## Live.ChainMixerDevice


### Live.ChainMixerDevice.ChainMixerDevice

> This class represents a Chain's Mixer Device in Live, which gives youaccess to the Volume, Panning, and Send properties of a Chain.

- **Live.ChainMixerDevice.ChainMixerDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the mixer device.
- **Live.ChainMixerDevice.ChainMixerDevice.chain_activator** _Property_RO_ — `get`
  > Const access to the Chain's Activator Device Parameter.
- **Live.ChainMixerDevice.ChainMixerDevice.panning** _Property_RO_ — `get`
  > Const access to the Chain's Panning Device Parameter.
- **Live.ChainMixerDevice.ChainMixerDevice.sends** _Property_RO_ — `get, observe`
  > Const access to the Chain's list of Send Amount Device Parameters.
- **Live.ChainMixerDevice.ChainMixerDevice.volume** _Property_RO_ — `get`
  > Const access to the Chain's Volume Device Parameter.

## Live.Clip


### Live.Clip.Clip

> This class represents a Clip in Live. It can be either an AudioClip or a MIDI Clip, in an Arrangement or the Session, dependingon the Track (Slot) it lives in.

- **Live.Clip.Clip.add_new_notes()** _Built-In_
  > add_new_notes( (Clip)arg1, (object)arg2) -> IntU64Vector : Expects a Python iterable holding a number of Live.Clip.MidiNoteSpecification objects. The objects will be used to construct new notes in the clip. C++ signature :  std::__1::vector<unsigned long long, std::__1::allocator<unsigned long long>> add_new_notes(TPyHandle<AClip>,boost::python::api::object)
- **Live.Clip.Clip.add_warp_marker()** _Built-In_
  > add_warp_marker( (Clip)self, (object)warp_marker) -> None : Available for AudioClips only. Adds the specified warp marker, if possible. C++ signature :  void add_warp_marker(TPyHandle<AClip>,boost::python::api::object)
- **Live.Clip.Clip.apply_note_modifications()** _Built-In_
  > apply_note_modifications( (Clip)arg1, (MidiNoteVector)arg2) -> None : Expects a list of notes as returned from get_notes_extended. The content of the list will be used to modify existing notes in the clip, based on matching note IDs. This function should be used when modifying existing notes, e.g. changing the velocity or start time. The function ensures that per-note events attached to the modified notes are preserved. This is NOT the case when replacing notes via a combination of remove_notes_extended and add_new_notes. The given list can be a subset of the notes in the clip, but it must not contain any notes that are not present in the clip.  C++ signature :  void apply_note_modifications(TPyHandle<AClip>,std::__1::vector<NClipApi::TNoteInfo, std::__1::allocator<NClipApi::TNoteInfo>>)
- **Live.Clip.Clip.automation_envelope()** _Built-In_
  > automation_envelope( (Clip)arg1, (DeviceParameter)arg2) -> Envelope : Return the envelope for the given parameter.Returns None if the envelope doesn't exist.Returns None for Arrangement clips.Returns None for parameters from a different track. C++ signature :  TWeakPtr<TPyHandle<AAutomation>> automation_envelope(TPyHandle<AClip>,TPyHandle<ATimeableValue>)
- **Live.Clip.Clip.beat_to_sample_time()** _Built-In_
  > beat_to_sample_time( (Clip)self, (float)beat_time) -> float : Available for AudioClips only. Converts the given beat time to sample time. Raises an error if the sample is not warped. C++ signature :  double beat_to_sample_time(TPyHandle<AClip>,double)
- **Live.Clip.Clip.clear_all_envelopes()** _Built-In_
  > clear_all_envelopes( (Clip)arg1) -> None : Clears all envelopes for this clip. C++ signature :  void clear_all_envelopes(TPyHandle<AClip>)
- **Live.Clip.Clip.clear_envelope()** _Built-In_
  > clear_envelope( (Clip)arg1, (DeviceParameter)arg2) -> None : Clears the envelope of this clips given parameter. C++ signature :  void clear_envelope(TPyHandle<AClip>,TPyHandle<ATimeableValue>)
- **Live.Clip.Clip.create_automation_envelope()** _Built-In_
  > create_automation_envelope( (Clip)arg1, (DeviceParameter)arg2) -> Envelope : Creates an envelope for a given parameter and returns it.This should only be used if the envelope doesn't exist.Raises an error if the envelope can't be created. C++ signature :  TWeakPtr<TPyHandle<AAutomation>> create_automation_envelope(TPyHandle<AClip>,TPyHandle<ATimeableValue>)
- **Live.Clip.Clip.crop()** _Built-In_
  > crop( (Clip)arg1) -> None : Crops the clip. The region that is cropped depends on whether the clip is looped or not. If looped, the region outside of the loop is removed. If not looped, the region outside the start and end markers is removed. C++ signature :  void crop(TPyHandle<AClip>)
- **Live.Clip.Clip.deselect_all_notes()** _Built-In_
  > deselect_all_notes( (Clip)arg1) -> None : De-selects all notes present in the clip. C++ signature :  void deselect_all_notes(TPyHandle<AClip>)
- **Live.Clip.Clip.duplicate_loop()** _Built-In_
  > duplicate_loop( (Clip)arg1) -> None : Make the loop two times longer and duplicates notes and envelopes. Duplicates the clip start/end range if the clip is not looped. C++ signature :  void duplicate_loop(TPyHandle<AClip>)
- **Live.Clip.Clip.duplicate_notes_by_id()** _Built-In_
  > duplicate_notes_by_id( (Clip)self, (object)note_ids [, (object)destination_time=None [, (int)transposition_amount=0]]) -> IntU64Vector : Duplicate all notes matching the given note IDs. If the optional destination_time is not provided, new notes will be inserted after the last selected note. This behavior can be observed when duplicating notes in the Live GUI. If the transposition_amount is specified, the notes in the region will be transposed by the number of semitones. Raises an error on audio clips. C++ signature :  std::__1::vector<unsigned long long, std::__1::allocator<unsigned long long>> duplicate_notes_by_id(TPyHandle<AClip>,boost::python::api::object [,boost::python::api::object=None [,int=0]])
- **Live.Clip.Clip.duplicate_region()** _Built-In_
  > duplicate_region( (Clip)self, (float)region_start, (float)region_length, (float)destination_time [, (int)pitch=-1 [, (int)transposition_amount=0]]) -> None : Duplicate the notes in the specified region to the destination_time. Only notes of the specified pitch are duplicated or all if pitch is -1. If the transposition_amount is not 0, the notes in the region will be transposed by the transpose_amount of semitones.Raises an error on audio clips. C++ signature :  void duplicate_region(TPyHandle<AClip>,double,double,double [,int=-1 [,int=0]])
- **Live.Clip.Clip.fire()** _Built-In_
  > fire( (Clip)arg1) -> None : (Re)Start playing this Clip. C++ signature :  void fire(TPyHandle<AClip>)
- **Live.Clip.Clip.get_all_notes_extended()** _Built-In_
  > get_all_notes_extended( (Clip)arg1) -> MidiNoteVector : Returns a list of all MIDI notes from the clip, regardless of their position relative to the start and end markers/loop start and loop end. Each note is represented by a Live.Clip.MidiNote object. The returned list can be modified freely, but modifications will not be reflected in the MIDI clip until apply_note_modifications is called. C++ signature :  std::__1::vector<NClipApi::TNoteInfo, std::__1::allocator<NClipApi::TNoteInfo>> get_all_notes_extended(TPyHandle<AClip>)
- **Live.Clip.Clip.get_notes()** _Built-In_
  > get_notes( (Clip)self, (float)from_time, (int)from_pitch, (float)time_span, (int)pitch_span) -> tuple : Returns a tuple of tuples where each inner tuple represents a note starting in the given pitch- and time range. The inner tuple contains pitch, time, duration, velocity, and mute state. C++ signature :  boost::python::tuple get_notes(TPyHandle<AClip>,double,int,double,int)
- **Live.Clip.Clip.get_notes_by_id()** _Built-In_
  > get_notes_by_id( (Clip)arg1, (object)note_ids) -> MidiNoteVector : Return a list of MIDI notes matching the given note IDs.  C++ signature :  std::__1::vector<NClipApi::TNoteInfo, std::__1::allocator<NClipApi::TNoteInfo>> get_notes_by_id(TPyHandle<AClip>,boost::python::api::object)
- **Live.Clip.Clip.get_notes_extended()** _Built-In_
  > get_notes_extended( (Clip)arg1, (int)from_pitch, (int)pitch_span, (float)from_time, (float)time_span) -> MidiNoteVector : Returns a list of MIDI notes from the given pitch and time range. Each note is represented by a Live.Clip.MidiNote object. The returned list can be modified freely, but modifications will not be reflected in the MIDI clip until apply_note_modifications is called. C++ signature :  std::__1::vector<NClipApi::TNoteInfo, std::__1::allocator<NClipApi::TNoteInfo>> get_notes_extended(TPyHandle<AClip>,int,int,double,double)
- **Live.Clip.Clip.get_selected_notes()** _Built-In_
  > get_selected_notes( (Clip)arg1) -> tuple : Returns a tuple of tuples where each inner tuple represents a selected note. The inner tuple contains pitch, time, duration, velocity, and mute state. C++ signature :  boost::python::tuple get_selected_notes(TPyHandle<AClip>)
- **Live.Clip.Clip.get_selected_notes_extended()** _Built-In_
  > get_selected_notes_extended( (Clip)arg1) -> MidiNoteVector : Returns a list of all MIDI notes from the clip that are currently selected. Each note is represented by a Live.Clip.MidiNote object. The returned list can be modified freely, but modifications will not be reflected in the MIDI clip until apply_note_modifications is called. C++ signature :  std::__1::vector<NClipApi::TNoteInfo, std::__1::allocator<NClipApi::TNoteInfo>> get_selected_notes_extended(TPyHandle<AClip>)
- **Live.Clip.Clip.move_playing_pos()** _Built-In_
  > move_playing_pos( (Clip)arg1, (float)arg2) -> None : Jump forward or backward by the specified relative amount in beats. Will do nothing, if the Clip is not playing. C++ signature :  void move_playing_pos(TPyHandle<AClip>,double)
- **Live.Clip.Clip.move_warp_marker()** _Built-In_
  > move_warp_marker( (Clip)self, (float)marker_beat_time, (float)beat_time_distance) -> None : Available for AudioClips only. Moves the specified warp marker by the specified beat time amount, if possible. C++ signature :  void move_warp_marker(TPyHandle<AClip>,double,double)
- **Live.Clip.Clip.note_number_to_name()** _Built-In_
  > note_number_to_name( (Clip)self, (int)midi_pitch) -> str : Return a human-readable name for the given MIDI note number. Takes into account the scale and tonal spelling settings of the clip, as well as the current tuning system (if any) C++ signature :  TString note_number_to_name(TPyHandle<AClip>,int)
- **Live.Clip.Clip.quantize()** _Built-In_
  > quantize( (Clip)arg1, (int)arg2, (float)arg3) -> None : Quantize all notes in a clip or align warp markers. C++ signature :  void quantize(TPyHandle<AClip>,int,float)
- **Live.Clip.Clip.quantize_pitch()** _Built-In_
  > quantize_pitch( (Clip)arg1, (int)arg2, (int)arg3, (float)arg4) -> None : Quantize all the notes of a given pitch.  Raises an error on audio clips. C++ signature :  void quantize_pitch(TPyHandle<AClip>,int,int,float)
- **Live.Clip.Clip.remove_notes()** _Built-In_
  > remove_notes( (Clip)arg1, (float)arg2, (int)arg3, (float)arg4, (int)arg5) -> None : Delete all notes starting in the given pitch- and time range. C++ signature :  void remove_notes(TPyHandle<AClip>,double,int,double,int)
- **Live.Clip.Clip.remove_notes_by_id()** _Built-In_
  > remove_notes_by_id( (Clip)arg1, (object)arg2) -> None : Delete all notes matching the given note IDs. This function should NOT be used to implement modification of existing notes (i.e. in combination with add_new_notes), as that leads to loss of per-note events. apply_note_modifications must be used instead for modifying existing notes. C++ signature :  void remove_notes_by_id(TPyHandle<AClip>,boost::python::api::object)
- **Live.Clip.Clip.remove_notes_extended()** _Built-In_
  > remove_notes_extended( (Clip)arg1, (int)from_pitch, (int)pitch_span, (float)from_time, (float)time_span) -> None : Delete all notes starting in the given pitch and time range. This function should NOT be used to implement modification of existing notes (i.e. in combination with add_new_notes), as that leads to loss of per-note events. apply_note_modifications must be used instead for modifying existing notes. C++ signature :  void remove_notes_extended(TPyHandle<AClip>,int,int,double,double)
- **Live.Clip.Clip.remove_warp_marker()** _Built-In_
  > remove_warp_marker( (Clip)self, (float)beat_time) -> None : Available for AudioClips only. Removes the specified warp marker, if possible. C++ signature :  void remove_warp_marker(TPyHandle<AClip>,double)
- **Live.Clip.Clip.replace_selected_notes()** _Built-In_
  > replace_selected_notes( (Clip)arg1, (tuple)arg2) -> None : Called with a tuple of tuples where each inner tuple represents a note in the same format as returned by get_selected_notes. The notes described that way will then be used to replace the old selection. C++ signature :  void replace_selected_notes(TPyHandle<AClip>,boost::python::tuple)
- **Live.Clip.Clip.sample_to_beat_time()** _Built-In_
  > sample_to_beat_time( (Clip)self, (float)sample_time) -> float : Available for AudioClips only. Converts the given sample time to beat time. Raises an error if the sample is not warped. C++ signature :  double sample_to_beat_time(TPyHandle<AClip>,double)
- **Live.Clip.Clip.scrub()** _Built-In_
  > scrub( (Clip)self, (float)scrub_position) -> None : Scrubs inside a clip. scrub_position defines the position in beats that the scrub will start from. The scrub will continue until stop_scrub is called. Global quantization applies to the scrub's position and length. C++ signature :  void scrub(TPyHandle<AClip>,double)
- **Live.Clip.Clip.seconds_to_sample_time()** _Built-In_
  > seconds_to_sample_time( (Clip)self, (float)seconds) -> float : Available for AudioClips only. Converts the given seconds to sample time. Raises an error if the sample is warped. C++ signature :  double seconds_to_sample_time(TPyHandle<AClip>,double)
- **Live.Clip.Clip.select_all_notes()** _Built-In_
  > select_all_notes( (Clip)arg1) -> None : Selects all notes present in the clip. C++ signature :  void select_all_notes(TPyHandle<AClip>)
- **Live.Clip.Clip.select_notes_by_id()** _Built-In_
  > select_notes_by_id( (Clip)arg1, (object)arg2) -> None : Selects all notes matching the given note IDs. C++ signature :  void select_notes_by_id(TPyHandle<AClip>,boost::python::api::object)
- **Live.Clip.Clip.set_fire_button_state()** _Built-In_
  > set_fire_button_state( (Clip)arg1, (bool)arg2) -> None : Set the clip's fire button state directly. Supports all launch modes. C++ signature :  void set_fire_button_state(TPyHandle<AClip>,bool)
- **Live.Clip.Clip.set_notes()** _Built-In_
  > set_notes( (Clip)arg1, (tuple)arg2) -> None : Called with a tuple of tuples where each inner tuple represents a note in the same format as returned by get_notes. The notes described that way will then be added to the clip. C++ signature :  void set_notes(TPyHandle<AClip>,boost::python::tuple)
- **Live.Clip.Clip.stop()** _Built-In_
  > stop( (Clip)arg1) -> None : Stop playing this Clip. C++ signature :  void stop(TPyHandle<AClip>)
- **Live.Clip.Clip.stop_scrub()** _Built-In_
  > stop_scrub( (Clip)arg1) -> None : Stops the current scrub. C++ signature :  void stop_scrub(TPyHandle<AClip>)
- **Live.Clip.Clip.automation_envelopes** _Property_RO_ — `get`
  > Const access to a list of all automation envelopes for this clip.
- **Live.Clip.Clip.available_warp_modes** _Property_RO_ — `get`
  > Available for AudioClips only.Get/Set the available warp modes, that can be used.
- **Live.Clip.Clip.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Clip.
- **Live.Clip.Clip.color** _Property_ — `get, set, observe`
  > Get/set access to the color of the Clip (RGB).
- **Live.Clip.Clip.color_index** _Property_ — `get, set, observe`
  > Get/set access to the color index of the Clip.
- **Live.Clip.Clip.end_marker** _Property_ — `get, set, observe`
  > Get/Set the Clips end marker pos in beats/seconds (unit depends on warping).
- **Live.Clip.Clip.end_time** _Property_RO_ — `get, observe`
  > Get the clip's end time.
- **Live.Clip.Clip.file_path** _Property_RO_ — `get, observe`
  > Get the path of the file represented by the Audio Clip.
- **Live.Clip.Clip.gain** _Property_ — `get, set, observe`
  > Available for AudioClips only.Read/write access to the gain setting of theAudio Clip
- **Live.Clip.Clip.gain_display_string** _Property_RO_ — `get`
  > Return a string with the gain as dB value
- **Live.Clip.Clip.groove** _Property_ — `get, set, observe`
  > Get the groove associated with this clip.
- **Live.Clip.Clip.has_envelopes** _Property_RO_ — `get, observe`
  > Will notify if the clip gets his first envelope or the last envelope is removed.
- **Live.Clip.Clip.has_groove** _Property_RO_ — `get`
  > Returns true if a groove is associated with this clip.
- **Live.Clip.Clip.is_arrangement_clip** _Property_RO_ — `get`
  > return true if this Clip is an Arrangement Clip.A Clip can be either a Session or Arrangement Clip.
- **Live.Clip.Clip.is_audio_clip** _Property_RO_ — `get`
  > Return true if this Clip is an Audio Clip.A Clip can be either an Audioclip or a MIDI Clip.
- **Live.Clip.Clip.is_midi_clip** _Property_RO_ — `get`
  > return true if this Clip is a MIDI Clip.A Clip can be either an Audioclip or a MIDI Clip.
- **Live.Clip.Clip.is_overdubbing** _Property_RO_ — `get, observe`
  > returns true if the Clip is recording overdubs
- **Live.Clip.Clip.is_playing** _Property_ — `get, set`
  > Get/Set if this Clip is currently playing. If the Clips trigger modeis set to a quantization value, the Clip will not start playing immediately.If you need to know wether the Clip was triggered, use the is_triggered property.
- **Live.Clip.Clip.is_recording** _Property_RO_ — `get, observe`
  > returns true if the Clip was triggered to record or is recording.
- **Live.Clip.Clip.is_session_clip** _Property_RO_ — `get`
  > return true if this Clip is a Session Clip.A Clip can be either a Session or Arrangement Clip.
- **Live.Clip.Clip.is_take_lane_clip** _Property_RO_ — `get`
  > return true if this Clip is a Take Lane Clip.A Take Lane Clip is also always an Arrangement Clip.
- **Live.Clip.Clip.is_triggered** _Property_RO_ — `get`
  > returns true if the Clip was triggered or is playing.
- **Live.Clip.Clip.launch_mode** _Property_ — `get, set, observe`
  > Get/Set access to the launch mode setting of the Clip.
- **Live.Clip.Clip.launch_quantization** _Property_ — `get, set, observe`
  > Get/Set access to the launch quantization setting of the Clip.
- **Live.Clip.Clip.legato** _Property_ — `get, set, observe`
  > Get/Set access to the legato setting of the Clip
- **Live.Clip.Clip.length** _Property_RO_ — `get`
  > Get to the Clips length in beats/seconds (unit depends on warping).
- **Live.Clip.Clip.loop_end** _Property_ — `get, set, observe`
  > Get/Set the loop end pos of this Clip in beats/seconds (unit depends on warping).
- **Live.Clip.Clip.loop_start** _Property_ — `get, set, observe`
  > Get/Set the Clips loopstart pos in beats/seconds (unit depends on warping).
- **Live.Clip.Clip.looping** _Property_ — `get, set, observe`
  > Get/Set the Clips 'loop is enabled' flag.Only Warped Audio Clips or MIDI Clip can be looped.
- **Live.Clip.Clip.muted** _Property_ — `get, set, observe`
  > Read/write access to the mute state of the Clip.
- **Live.Clip.Clip.name** _Property_ — `get, set, observe`
  > Read/write access to the name of the Clip.
- **Live.Clip.Clip.pitch_coarse** _Property_ — `get, set, observe`
  > Available for AudioClips only.Read/write access to the pitch (in halftones) setting of theAudio Clip, ranging from -48 to 48
- **Live.Clip.Clip.pitch_fine** _Property_ — `get, set, observe`
  > Available for AudioClips only.Read/write access to the pitch fine setting of theAudio Clip, ranging from -500 to 500
- **Live.Clip.Clip.playing_position** _Property_RO_ — `get, observe`
  > Constant access to the current playing position of the clip.The returned value is the position in beats for midi and warped audio clips,or in seconds for unwarped audio clips. Stopped clips will return 0.
- **Live.Clip.Clip.position** _Property_ — `get, set, observe`
  > Get/Set the loop position of this Clip in beats/seconds (unit depends on warping).
- **Live.Clip.Clip.ram_mode** _Property_ — `get, set, observe`
  > Available for AudioClips only.Read/write access to the Ram mode setting of the Audio Clip
- **Live.Clip.Clip.sample_length** _Property_RO_ — `get`
  > Available for AudioClips only.Get the sample length in sample time or -1 if there is no sample available.
- **Live.Clip.Clip.sample_rate** _Property_RO_ — `get`
  > Available for AudioClips only.Read-only access to the Clip's sampling rate.
- **Live.Clip.Clip.signature_denominator** _Property_ — `get, set, observe`
  > Get/Set access to the global signature denominator of the Clip.
- **Live.Clip.Clip.signature_numerator** _Property_ — `get, set, observe`
  > Get/Set access to the global signature numerator of the Clip.
- **Live.Clip.Clip.start_marker** _Property_ — `get, set, observe`
  > Get/Set the Clips start marker pos in beats/seconds (unit depends on warping).
- **Live.Clip.Clip.start_time** _Property_RO_ — `get, observe`
  > Get the clip's start time offset. For Session View clips, this is the time the clip was started. For Arrangement View clips, this is the offset within the arrangement.
- **Live.Clip.Clip.velocity_amount** _Property_ — `get, set, observe`
  > Get/Set access to the velocity to volume amount of the Clip.
- **Live.Clip.Clip.view** _Property_RO_ — `get`
  > Get the view of the Clip.
- **Live.Clip.Clip.warp_markers** _Property_RO_ — `get, observe`
  > Available for AudioClips only.Get the warp markers for this audio clip.
- **Live.Clip.Clip.warp_mode** _Property_ — `get, set, observe`
  > Available for AudioClips only.Get/Set the warp mode for this audio clip.
- **Live.Clip.Clip.warping** _Property_ — `get, set, observe`
  > Available for AudioClips only.Get/Set if this Clip is timestreched.
- **Live.Clip.Clip.will_record_on_start** _Property_RO_ — `get`
  > returns true if the Clip will record on being started.

#### Live.Clip.Clip.View

> Representing the view aspects of a Clip.

- **Live.Clip.Clip.View.hide_envelope()** _Built-In_
  > hide_envelope( (View)arg1) -> None : Hide the envelope view. C++ signature :  void hide_envelope(TPyViewData<AClip>)
- **Live.Clip.Clip.View.select_envelope_parameter()** _Built-In_
  > select_envelope_parameter( (View)arg1, (DeviceParameter)arg2) -> None : Select the given device parameter in the envelope view. C++ signature :  void select_envelope_parameter(TPyViewData<AClip>,TPyHandle<ATimeableValue>)
- **Live.Clip.Clip.View.show_envelope()** _Built-In_
  > show_envelope( (View)arg1) -> None : Show the envelope view. C++ signature :  void show_envelope(TPyViewData<AClip>)
- **Live.Clip.Clip.View.show_loop()** _Built-In_
  > show_loop( (View)arg1) -> None : Show the entire loop in the detail view. C++ signature :  void show_loop(TPyViewData<AClip>)
- **Live.Clip.Clip.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the clip view.
- **Live.Clip.Clip.View.grid_is_triplet** _Property_ — `get, set`
  > Get/set wether the grid is showing in triplet mode.
- **Live.Clip.Clip.View.grid_quantization** _Property_ — `get, set`
  > Get/set clip grid quantization resolution.

### Live.Clip.ClipLaunchQuantization

  - Enum (15): `q_global=q_global`, `q_none=q_none`, `q_8_bars=q_8_bars`, `q_4_bars=q_4_bars`, `q_2_bars=q_2_bars`, `q_bar=q_bar`, `q_half=q_half`, `q_half_triplet=q_half_triplet`, `q_quarter=q_quarter`, `q_quarter_triplet=q_quarter_triplet`, `q_eighth=q_eighth`, `q_eighth_triplet=q_eighth_triplet`, `q_sixteenth=q_sixteenth`, `q_sixteenth_triplet=q_sixteenth_triplet`, `q_thirtysecond=q_thirtysecond`

### Live.Clip.GridQuantization

  - Enum (11): `no_grid=no_grid`, `g_8_bars=g_8_bars`, `g_4_bars=g_4_bars`, `g_2_bars=g_2_bars`, `g_bar=g_bar`, `g_half=g_half`, `g_quarter=g_quarter`, `g_eighth=g_eighth`, `g_sixteenth=g_sixteenth`, `g_thirtysecond=g_thirtysecond`, `count=count`

### Live.Clip.LaunchMode

  - Enum (4): `trigger=trigger`, `gate=gate`, `toggle=toggle`, `repeat=repeat`

### Live.Clip.MidiNote

> An object representing a MIDI Note

- **Live.Clip.MidiNote.duration** _Property_ — `get, set`
- **Live.Clip.MidiNote.mute** _Property_ — `get, set`
- **Live.Clip.MidiNote.note_id** _Property_RO_ — `get`
  > A numerical ID that's unique within the originating clip of the note. Not to beused directly, but important for other API calls, namely apply_note_modifications.
- **Live.Clip.MidiNote.pitch** _Property_ — `get, set`
- **Live.Clip.MidiNote.probability** _Property_ — `get, set`
- **Live.Clip.MidiNote.release_velocity** _Property_ — `get, set`
- **Live.Clip.MidiNote.start_time** _Property_ — `get, set`
- **Live.Clip.MidiNote.velocity** _Property_ — `get, set`
- **Live.Clip.MidiNote.velocity_deviation** _Property_ — `get, set`

### Live.Clip.MidiNoteSpecification

> An object specifying the data for creating a MIDI note. To be used with the add_new_notes function.


### Live.Clip.MidiNoteVector

> A container for holding MIDI notes from Live.

- **Live.Clip.MidiNoteVector.append()** _Built-In_
  > append( (MidiNoteVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<NClipApi::TNoteInfo, std::__1::allocator<NClipApi::TNoteInfo>> {lvalue},boost::python::api::object)
- **Live.Clip.MidiNoteVector.extend()** _Built-In_
  > extend( (MidiNoteVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<NClipApi::TNoteInfo, std::__1::allocator<NClipApi::TNoteInfo>> {lvalue},boost::python::api::object)

### Live.Clip.WarpMarker

> This class represents a WarpMarker type.

- **Live.Clip.WarpMarker.beat_time** _Property_RO_ — `get`
  > A WarpMarker's beat time.
- **Live.Clip.WarpMarker.sample_time** _Property_RO_ — `get`
  > A WarpMarker's sample time.

### Live.Clip.WarpMarkerVector

> A container for returning warp markers from Live.

- **Live.Clip.WarpMarkerVector.append()** _Built-In_
  > append( (WarpMarkerVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<NApiHelpers::TWarpMarker, std::__1::allocator<NApiHelpers::TWarpMarker>> {lvalue},boost::python::api::object)
- **Live.Clip.WarpMarkerVector.extend()** _Built-In_
  > extend( (WarpMarkerVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<NApiHelpers::TWarpMarker, std::__1::allocator<NApiHelpers::TWarpMarker>> {lvalue},boost::python::api::object)

### Live.Clip.WarpMode

  - Enum (8): `beats=beats`, `tones=tones`, `texture=texture`, `repitch=repitch`, `complex=complex`, `rex=rex`, `complex_pro=complex_pro`, `count=count`

## Live.ClipSlot


### Live.ClipSlot.ClipSlot

> This class represents an entry in Lives Session view matrix.

- **Live.ClipSlot.ClipSlot.create_audio_clip()** _Built-In_
  > create_audio_clip( (ClipSlot)arg1, (object)arg2) -> Clip : Creates an audio clip referencing the file at the given absolute path in the slot. Throws an error when called on non-empty slots or slots in non-audio or frozen tracks, or when the path doesn't point at a valid audio file. C++ signature :  TWeakPtr<TPyHandle<AClip>> create_audio_clip(TPyHandle<AGroupAndClipSlotBase>,TString)
- **Live.ClipSlot.ClipSlot.create_clip()** _Built-In_
  > create_clip( (ClipSlot)arg1, (float)arg2) -> Clip : Creates an empty clip with the given length in the slot. Throws an error when called on non-empty slots or slots in non-MIDI tracks. C++ signature :  TWeakPtr<TPyHandle<AClip>> create_clip(TPyHandle<AGroupAndClipSlotBase>,double)
- **Live.ClipSlot.ClipSlot.delete_clip()** _Built-In_
  > delete_clip( (ClipSlot)arg1) -> None : Removes the clip contained in the slot. Raises an exception if the slot was empty. C++ signature :  void delete_clip(TPyHandle<AGroupAndClipSlotBase>)
- **Live.ClipSlot.ClipSlot.duplicate_clip_to()** _Built-In_
  > duplicate_clip_to( (ClipSlot)arg1, (ClipSlot)arg2) -> None : Duplicates the slot's clip to the passed in target slot. Overrides the target's clip if it's not empty. Raises an exception if the (source) slot itself is empty, or if source and target have different track types (audio vs. MIDI). Also raises if the source or target slot is in a group track (so called group slot). C++ signature :  void duplicate_clip_to(TPyHandle<AGroupAndClipSlotBase>,TPyHandle<AGroupAndClipSlotBase>)
- **Live.ClipSlot.ClipSlot.fire()** _Built-In_
  > fire( (ClipSlot)arg1) -> None : Fire a Clip if this Clipslot owns one, else trigger the stop button, if we have one. C++ signature :  void fire(TPyHandle<AGroupAndClipSlotBase>)fire( (ClipSlot)self [, (float)record_length=1.7976931348623157e+308 [, (int)launch_quantization=-2147483648 [, (bool)force_legato=False]]]) -> None : If 'record_length' is passed, the clip will be refired after the given recording length.  Raises an error if the slot owns a clip. 'launch_quantization' determines the quantization of global transport that is applied overriding the value in the song. 'force_legato' will make the clip play inmediatelly. The playhead will be moved to keep the clip synchronized. C++ signature :  void fire(TPyHandle<AGroupAndClipSlotBase> [,double=1.7976931348623157e+308 [,int=-2147483648 [,bool=False]]])
- **Live.ClipSlot.ClipSlot.set_fire_button_state()** _Built-In_
  > set_fire_button_state( (ClipSlot)arg1, (bool)arg2) -> None : Set the clipslot's fire button state directly. Supports all launch modes. C++ signature :  void set_fire_button_state(TPyHandle<AGroupAndClipSlotBase>,bool)
- **Live.ClipSlot.ClipSlot.stop()** _Built-In_
  > stop( (ClipSlot)arg1) -> None : Stop playing the contained Clip, if there is a Clip and its currently playing. C++ signature :  void stop(TPyHandle<AGroupAndClipSlotBase>)
- **Live.ClipSlot.ClipSlot.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the ClipSlot.
- **Live.ClipSlot.ClipSlot.clip** _Property_RO_ — `get`
  > Returns the Clip which this clipslots currently owns. Might be None.
- **Live.ClipSlot.ClipSlot.color** _Property_RO_ — `get, observe`
  > Returns the canonical color for the clip slot or None if it does not exist.
- **Live.ClipSlot.ClipSlot.color_index** _Property_RO_ — `get, observe`
  > Returns the canonical color index for the clip slot or None if it does not exist.
- **Live.ClipSlot.ClipSlot.controls_other_clips** _Property_RO_ — `get, observe`
  > Returns true if firing this slot will fire clips in other slots.Can only be true for slots in group tracks.
- **Live.ClipSlot.ClipSlot.has_clip** _Property_RO_ — `get, observe`
  > Returns true if this Clipslot owns a Clip.
- **Live.ClipSlot.ClipSlot.has_stop_button** _Property_ — `get, set, observe`
  > Get/Set if this Clip has a stop button, which will, if fired, stop anyother Clip that is currently playing the Track we do belong to.
- **Live.ClipSlot.ClipSlot.is_group_slot** _Property_RO_ — `get`
  > Returns whether this clip slot is a group track slot (group slot).
- **Live.ClipSlot.ClipSlot.is_playing** _Property_RO_ — `get`
  > Returns whether the clip associated with the slot is playing.
- **Live.ClipSlot.ClipSlot.is_recording** _Property_RO_ — `get`
  > Returns whether the clip associated with the slot is recording.
- **Live.ClipSlot.ClipSlot.is_triggered** _Property_RO_ — `get, observe`
  > Const access to the triggering state of the clip slot.
- **Live.ClipSlot.ClipSlot.playing_status** _Property_RO_ — `get, observe`
  > Const access to the playing state of the clip slot.Can be either stopped, playing, or recording.
- **Live.ClipSlot.ClipSlot.will_record_on_start** _Property_RO_ — `get`
  > returns true if the clip slot will record on being fired.

### Live.ClipSlot.ClipSlotPlayingState

  - Enum (3): `stopped=stopped`, `started=started`, `recording=recording`

## Live.CompressorDevice


### Live.CompressorDevice.CompressorDevice

> This class represents a Compressor device.

- **Live.CompressorDevice.CompressorDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.CompressorDevice.CompressorDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.CompressorDevice.CompressorDevice.available_input_routing_channels** _Property_RO_ — `get, observe`
  > Return a list of source channels for input routing in the sidechain.
- **Live.CompressorDevice.CompressorDevice.available_input_routing_types** _Property_RO_ — `get, observe`
  > Return a list of source types for input routing in the sidechain.
- **Live.CompressorDevice.CompressorDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.CompressorDevice.CompressorDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.CompressorDevice.CompressorDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.CompressorDevice.CompressorDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.CompressorDevice.CompressorDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.CompressorDevice.CompressorDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.CompressorDevice.CompressorDevice.input_routing_channel** _Property_ — `get, set, observe`
  > Get and set the current source channel for input routing in the sidechain.Raises ValueError if the channel isn't one of the current values inavailable_input_routing_channels.
- **Live.CompressorDevice.CompressorDevice.input_routing_type** _Property_ — `get, set, observe`
  > Get and set the current source type for input routing in the sidechain.Raises ValueError if the type isn't one of the current values inavailable_input_routing_types.
- **Live.CompressorDevice.CompressorDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.CompressorDevice.CompressorDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.CompressorDevice.CompressorDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.CompressorDevice.CompressorDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.CompressorDevice.CompressorDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.CompressorDevice.CompressorDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.CompressorDevice.CompressorDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.CompressorDevice.CompressorDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.CompressorDevice.CompressorDevice.View

> Representing the view aspects of a device.

- **Live.CompressorDevice.CompressorDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.CompressorDevice.CompressorDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.Conversions

- **Live.Conversions.audio_to_midi_clip()** _Built-In_
  > audio_to_midi_clip( (Song)song, (Clip)audio_clip, (int)audio_to_midi_type) -> None : Creates a MIDI clip in a new MIDI track with the notes extracted from the given audio_clip. The `audio_to_midi_type` decides which algorithm is used in the process. Raises error when called with an inconvertible clip or invalid `audio_to_midi_type`. C++ signature :  void audio_to_midi_clip(TPyHandle<ASong>,TPyHandle<AClip>,int)
- **Live.Conversions.create_drum_rack_from_audio_clip()** _Built-In_
  > create_drum_rack_from_audio_clip( (Song)song, (Clip)audio_clip) -> None : Creates a new track with a drum rack with a simpler on the first pad with the specified audio clip. C++ signature :  void create_drum_rack_from_audio_clip(TPyHandle<ASong>,TPyHandle<AClip>)
- **Live.Conversions.create_midi_track_from_drum_pad()** _Built-In_
  > create_midi_track_from_drum_pad( (Song)song, (DrumPad)drum_pad) -> None : Creates a new Midi track containing the specified Drum Pad's device chain. C++ signature :  void create_midi_track_from_drum_pad(TPyHandle<ASong>,TPyHandle<ADrumGroupDevicePad>)
- **Live.Conversions.create_midi_track_with_simpler()** _Built-In_
  > create_midi_track_with_simpler( (Song)song, (Clip)audio_clip) -> None : Creates a new Midi track with a simpler including the specified audio clip. C++ signature :  void create_midi_track_with_simpler(TPyHandle<ASong>,TPyHandle<AClip>)
- **Live.Conversions.is_convertible_to_midi()** _Built-In_
  > is_convertible_to_midi( (Song)song, (Clip)audio_clip) -> bool : Returns whether `audio_clip` can be converted to MIDI. Raises error when called with a MIDI clip C++ signature :  bool is_convertible_to_midi(TPyHandle<ASong>,TPyHandle<AClip>)
- **Live.Conversions.move_devices_on_track_to_new_drum_rack_pad()** _Built-In_
  > move_devices_on_track_to_new_drum_rack_pad( (Song)song, (int)track_index) -> LomObject : Moves the entire device chain of the track according to the track index onto the C1 (note 36) drum pad of a new drum rack in a new track.If the track associated with the track index does not contain any devices nothing changes (i.e. a new track and new drum rack are not created). C++ signature :  TWeakPtr<TPyHandleBase> move_devices_on_track_to_new_drum_rack_pad(TPyHandle<ASong>,int)
- **Live.Conversions.sliced_simpler_to_drum_rack()** _Built-In_
  > sliced_simpler_to_drum_rack( (Song)song, (SimplerDevice)simpler) -> None : Converts the Simpler into a Drum Rack, assigning each slice to a drum pad. Calling it on a non-sliced simpler raises an error. C++ signature :  void sliced_simpler_to_drum_rack(TPyHandle<ASong>,TSimplerDevicePyHandle)

### Live.Conversions.AudioToMidiType

  - Enum (3): `harmony_to_midi=harmony_to_midi`, `melody_to_midi=melody_to_midi`, `drums_to_midi=drums_to_midi`

## Live.Device


### Live.Device.ATimeableValueVector

- **Live.Device.ATimeableValueVector.append()** _Built-In_
  > append( (ATimeableValueVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<TWeakPtr<ATimeableValue>, std::__1::allocator<TWeakPtr<ATimeableValue>>> {lvalue},boost::python::api::object)
- **Live.Device.ATimeableValueVector.extend()** _Built-In_
  > extend( (ATimeableValueVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<TWeakPtr<ATimeableValue>, std::__1::allocator<TWeakPtr<ATimeableValue>>> {lvalue},boost::python::api::object)

### Live.Device.Device

> This class represents a MIDI or Audio DSP-Device in Live.

- **Live.Device.Device.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.Device.Device.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.Device.Device.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.Device.Device.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.Device.Device.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.Device.Device.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.Device.Device.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.Device.Device.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.Device.Device.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.Device.Device.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.Device.Device.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.Device.Device.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.Device.Device.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.Device.Device.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.Device.Device.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.Device.Device.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.Device.Device.View

> Representing the view aspects of a device.

- **Live.Device.Device.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.Device.Device.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

### Live.Device.DeviceType

> The type of the device.

  - Enum (4): `undefined=undefined`, `instrument=instrument`, `audio_effect=audio_effect`, `midi_effect=midi_effect`

## Live.DeviceIO


### Live.DeviceIO.DeviceIO

> This class represents a specific input or output bus of a device.

- **Live.DeviceIO.DeviceIO.available_routing_channels** _Property_RO_ — `get, observe`
  > Return a list of channels for this IO endpoint.
- **Live.DeviceIO.DeviceIO.available_routing_types** _Property_RO_ — `get, observe`
  > Return a list of available routing types for this IO endpoint.
- **Live.DeviceIO.DeviceIO.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the device IO.
- **Live.DeviceIO.DeviceIO.default_external_routing_channel_is_none** _Property_ — `get, set`
  > Get and set whether the default routing channel for External routing types is none.
- **Live.DeviceIO.DeviceIO.routing_channel** _Property_ — `get, set, observe`
  > Get and set the current routing channel.Raises ValueError if the channel isn't one of the current values inavailable_routing_channels.
- **Live.DeviceIO.DeviceIO.routing_type** _Property_ — `get, set, observe`
  > Get and set the current routing type.Raises ValueError if the type isn't one of the current values inavailable_routing_types.

## Live.DeviceParameter


### Live.DeviceParameter.AutomationState

  - Enum (3): `none=none`, `playing=playing`, `overridden=overridden`

### Live.DeviceParameter.DeviceParameter

> This class represents a (automatable) parameter within a MIDI orAudio DSP-Device.

- **Live.DeviceParameter.DeviceParameter.begin_gesture()** _Built-In_
  > begin_gesture( (DeviceParameter)arg1) -> None : Notify the begin of a modification of the parameter, when a sequence of modifications have to be consider a consistent group -- for Sexample, when recording automation. C++ signature :  void begin_gesture(TPyHandle<ATimeableValue>)
- **Live.DeviceParameter.DeviceParameter.end_gesture()** _Built-In_
  > end_gesture( (DeviceParameter)arg1) -> None : Notify the end of a modification of the parameter. See begin_gesture. C++ signature :  void end_gesture(TPyHandle<ATimeableValue>)
- **Live.DeviceParameter.DeviceParameter.re_enable_automation()** _Built-In_
  > re_enable_automation( (DeviceParameter)arg1) -> None : Reenable automation for this parameter. C++ signature :  void re_enable_automation(TPyHandle<ATimeableValue>)
- **Live.DeviceParameter.DeviceParameter.str_for_value()** _Built-In_
  > str_for_value( (DeviceParameter)arg1, (float)arg2) -> str : Return a string representation of the given value. To be used for display purposes only.  This value can include characters like 'db' or 'hz', depending on the type of the parameter. C++ signature :  TString str_for_value(TPyHandle<ATimeableValue>,float)
- **Live.DeviceParameter.DeviceParameter.automation_state** _Property_RO_ — `get, observe`
  > Returns state of type AutomationState.
- **Live.DeviceParameter.DeviceParameter.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the device parameter.
- **Live.DeviceParameter.DeviceParameter.default_value** _Property_RO_ — `get`
  > Return the default value for this parameter.  A Default value is onlyavailable for non-quantized parameter types (see 'is_quantized').
- **Live.DeviceParameter.DeviceParameter.display_value** _Property_ — `get, set, observe`
  > Get/Set the current value (as visible in the GUI) this parameter.The value must be inside the min/max properties of this device.
- **Live.DeviceParameter.DeviceParameter.is_enabled** _Property_RO_ — `get`
  > Returns false if the parameter has been macro mapped or disabled by Max.
- **Live.DeviceParameter.DeviceParameter.is_quantized** _Property_RO_ — `get`
  > Returns True, if this value is a boolean or integer like switch.Non quantized values are continues float values.
- **Live.DeviceParameter.DeviceParameter.max** _Property_RO_ — `get`
  > Returns const access to the upper value of the allowed range forthis parameter
- **Live.DeviceParameter.DeviceParameter.min** _Property_RO_ — `get`
  > Returns const access to the lower value of the allowed range forthis parameter
- **Live.DeviceParameter.DeviceParameter.name** _Property_RO_ — `get, observe`
  > Returns const access the name of this parameter, as visible in Livesautomation choosers.
- **Live.DeviceParameter.DeviceParameter.original_name** _Property_RO_ — `get`
  > Returns const access the original name of this parameter, unaffected ofany renamings.
- **Live.DeviceParameter.DeviceParameter.short_value_items** _Property_RO_ — `get`
  > Return the list of possible values for this parameter. Like value_items, but prefers short value names if available. Raises an error if 'is_quantized' is False.
- **Live.DeviceParameter.DeviceParameter.state** _Property_RO_ — `get, observe`
  > Returns the state of the parameter:- enabled - the parameter's value can be changed,- irrelevant - the parameter is enabled, but value changes will not take any effect until it gets enabled,- disabled - the parameter's value cannot be changed.
- **Live.DeviceParameter.DeviceParameter.value** _Property_ — `get, set, observe`
  > Get/Set the current internal value of this parameter.The value must be inside the min/max properties of this device.
- **Live.DeviceParameter.DeviceParameter.value_items** _Property_RO_ — `get`
  > Return the list of possible values for this parameter. Raises an error if 'is_quantized' is False.

### Live.DeviceParameter.ParameterState

  - Enum (3): `enabled=enabled`, `irrelevant=irrelevant`, `disabled=disabled`

## Live.DriftDevice


### Live.DriftDevice.DriftDevice

> This class represents a Drift device.

- **Live.DriftDevice.DriftDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.DriftDevice.DriftDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.DriftDevice.DriftDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.DriftDevice.DriftDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.DriftDevice.DriftDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.DriftDevice.DriftDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.DriftDevice.DriftDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.DriftDevice.DriftDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.DriftDevice.DriftDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.DriftDevice.DriftDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.DriftDevice.DriftDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.DriftDevice.DriftDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.DriftDevice.DriftDevice.mod_matrix_filter_source_1_index** _Property_ — `get, set, observe`
  > Return the filter mod source 1 index
- **Live.DriftDevice.DriftDevice.mod_matrix_filter_source_1_list** _Property_RO_ — `get`
  > Return the filter mod source 1 list
- **Live.DriftDevice.DriftDevice.mod_matrix_filter_source_2_index** _Property_ — `get, set, observe`
  > Return the filter mod source 2 index
- **Live.DriftDevice.DriftDevice.mod_matrix_filter_source_2_list** _Property_RO_ — `get`
  > Return the filter mod source 2 list
- **Live.DriftDevice.DriftDevice.mod_matrix_lfo_source_index** _Property_ — `get, set, observe`
  > Return the lfo mod source index
- **Live.DriftDevice.DriftDevice.mod_matrix_lfo_source_list** _Property_RO_ — `get`
  > Return the lfo mod source list
- **Live.DriftDevice.DriftDevice.mod_matrix_pitch_source_1_index** _Property_ — `get, set, observe`
  > Return the pitch mod source 1 index
- **Live.DriftDevice.DriftDevice.mod_matrix_pitch_source_1_list** _Property_RO_ — `get`
  > Return the pitch mod source 1 list
- **Live.DriftDevice.DriftDevice.mod_matrix_pitch_source_2_index** _Property_ — `get, set, observe`
  > Return the pitch mod source 2 index
- **Live.DriftDevice.DriftDevice.mod_matrix_pitch_source_2_list** _Property_RO_ — `get`
  > Return the pitch mod source 2 list
- **Live.DriftDevice.DriftDevice.mod_matrix_shape_source_index** _Property_ — `get, set, observe`
  > Return the shape mod source index
- **Live.DriftDevice.DriftDevice.mod_matrix_shape_source_list** _Property_RO_ — `get`
  > Return the shape mod source list
- **Live.DriftDevice.DriftDevice.mod_matrix_source_1_index** _Property_ — `get, set, observe`
  > Return the custom mod source 1 index
- **Live.DriftDevice.DriftDevice.mod_matrix_source_1_list** _Property_RO_ — `get`
  > Return the custom mod source 1 list
- **Live.DriftDevice.DriftDevice.mod_matrix_source_2_index** _Property_ — `get, set, observe`
  > Return the custom mod source 2 index
- **Live.DriftDevice.DriftDevice.mod_matrix_source_2_list** _Property_RO_ — `get`
  > Return the custom mod source 2 list
- **Live.DriftDevice.DriftDevice.mod_matrix_source_3_index** _Property_ — `get, set, observe`
  > Return the custom mod source 3 index
- **Live.DriftDevice.DriftDevice.mod_matrix_source_3_list** _Property_RO_ — `get`
  > Return the custom mod source 3 list
- **Live.DriftDevice.DriftDevice.mod_matrix_target_1_index** _Property_ — `get, set, observe`
  > Return the custom mod target 1 index
- **Live.DriftDevice.DriftDevice.mod_matrix_target_1_list** _Property_RO_ — `get`
  > Return the custom mod target 1 list
- **Live.DriftDevice.DriftDevice.mod_matrix_target_2_index** _Property_ — `get, set, observe`
  > Return the custom mod target 2 index
- **Live.DriftDevice.DriftDevice.mod_matrix_target_2_list** _Property_RO_ — `get`
  > Return the custom mod target 2 list
- **Live.DriftDevice.DriftDevice.mod_matrix_target_3_index** _Property_ — `get, set, observe`
  > Return the custom mod target 3 index
- **Live.DriftDevice.DriftDevice.mod_matrix_target_3_list** _Property_RO_ — `get`
  > Return the custom mod target 3 list
- **Live.DriftDevice.DriftDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.DriftDevice.DriftDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.DriftDevice.DriftDevice.pitch_bend_range** _Property_ — `get, set, observe`
  > Return the Pitch Bend Range
- **Live.DriftDevice.DriftDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.DriftDevice.DriftDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.
- **Live.DriftDevice.DriftDevice.voice_count_index** _Property_ — `get, set, observe`
  > Return the voice count index
- **Live.DriftDevice.DriftDevice.voice_count_list** _Property_RO_ — `get`
  > Return the voice count list
- **Live.DriftDevice.DriftDevice.voice_mode_index** _Property_ — `get, set, observe`
  > Return the voice mode index
- **Live.DriftDevice.DriftDevice.voice_mode_list** _Property_RO_ — `get`
  > Return the voice mode list

#### Live.DriftDevice.DriftDevice.View

> Representing the view aspects of a device.

- **Live.DriftDevice.DriftDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.DriftDevice.DriftDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.DrumCellDevice


### Live.DrumCellDevice.DrumCellDevice

> This class represents a DrumCell device.

- **Live.DrumCellDevice.DrumCellDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.DrumCellDevice.DrumCellDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.DrumCellDevice.DrumCellDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.DrumCellDevice.DrumCellDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.DrumCellDevice.DrumCellDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.DrumCellDevice.DrumCellDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.DrumCellDevice.DrumCellDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.DrumCellDevice.DrumCellDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.DrumCellDevice.DrumCellDevice.gain** _Property_ — `get, set, observe`
  > Return the Gain value
- **Live.DrumCellDevice.DrumCellDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.DrumCellDevice.DrumCellDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.DrumCellDevice.DrumCellDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.DrumCellDevice.DrumCellDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.DrumCellDevice.DrumCellDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.DrumCellDevice.DrumCellDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.DrumCellDevice.DrumCellDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.DrumCellDevice.DrumCellDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.DrumCellDevice.DrumCellDevice.View

> Representing the view aspects of a device.

- **Live.DrumCellDevice.DrumCellDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.DrumCellDevice.DrumCellDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.DrumChain


### Live.DrumChain.DrumChain

> This class represents a drum group device chain in Live.

- **Live.DrumChain.DrumChain.delete_device()** _Built-In_
  > delete_device( (Chain)arg1, (int)arg2) -> None : Remove a device identified by its index from the chain. Throws runtime error if bad index.  C++ signature :  void delete_device(TChainPyHandle,int)
- **Live.DrumChain.DrumChain.duplicate_device()** _Built-In_
  > duplicate_device( (Chain)arg1, (int)arg2) -> None : Duplicate the device at the given index in the chain. C++ signature :  void duplicate_device(TChainPyHandle,int)
- **Live.DrumChain.DrumChain.insert_device()** _Built-In_
  > insert_device( (Chain)arg1, (str)DeviceName [, (int)DeviceIndex=-1]) -> LomObject : Add a device at a given index in the chain. At end if -1. C++ signature :  TWeakPtr<TPyHandleBase> insert_device(TChainPyHandle,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>> [,int=-1])
- **Live.DrumChain.DrumChain.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the chain.
- **Live.DrumChain.DrumChain.choke_group** _Property_ — `get, set, observe`
  > Access to the chain's choke group setting.
- **Live.DrumChain.DrumChain.color** _Property_ — `get, set, observe`
  > Access the color index of the Chain.
- **Live.DrumChain.DrumChain.color_index** _Property_ — `get, set, observe`
  > Access the color index of the Chain.
- **Live.DrumChain.DrumChain.devices** _Property_RO_ — `get, observe`
  > Return const access to all available Devices that are present in the chains
- **Live.DrumChain.DrumChain.has_audio_input** _Property_RO_ — `get`
  > return True, if this Chain can be feed with an Audio signal. This istrue for all Audio Chains.
- **Live.DrumChain.DrumChain.has_audio_output** _Property_RO_ — `get`
  > return True, if this Chain sends out an Audio signal. This istrue for all Audio Chains, and MIDI chains with an Instrument.
- **Live.DrumChain.DrumChain.has_midi_input** _Property_RO_ — `get`
  > return True, if this Chain can be feed with an Audio signal. This istrue for all MIDI Chains.
- **Live.DrumChain.DrumChain.has_midi_output** _Property_RO_ — `get`
  > return True, if this Chain sends out MIDI events. This istrue for all MIDI Chains with no Instruments.
- **Live.DrumChain.DrumChain.in_note** _Property_ — `get, set, observe`
  > Access to the incoming MIDI note that will trigger this chain.
- **Live.DrumChain.DrumChain.is_auto_colored** _Property_ — `get, set, observe`
  > Get/set access to the auto color flag of the Chain.If True, the Chain will always have the same color as the containingTrack or Chain.
- **Live.DrumChain.DrumChain.mixer_device** _Property_RO_ — `get`
  > Return access to the mixer device that holds the chain's mixer parameters:the Volume, Pan, and Sendamounts.
- **Live.DrumChain.DrumChain.mute** _Property_ — `get, set, observe`
  > Mute/unmute the chain.
- **Live.DrumChain.DrumChain.muted_via_solo** _Property_RO_ — `get, observe`
  > Return const access to whether this chain is muted due to some other chainbeing soloed.
- **Live.DrumChain.DrumChain.name** _Property_ — `get, set, observe`
  > Read/write access to the name of the Chain, as visible in the track header.
- **Live.DrumChain.DrumChain.out_note** _Property_ — `get, set, observe`
  > Access to the MIDI note sent to the devices in the chain.
- **Live.DrumChain.DrumChain.solo** _Property_ — `get, set, observe`
  > Get/Set the solo status of the chain. Note that this will not disable thesolo state of any other Chain in the same rack. If you want exclusive solo, you have to disable the solo state of the other Chains manually.

## Live.DrumPad


### Live.DrumPad.DrumPad

> This class represents a drum group device pad in Live.

- **Live.DrumPad.DrumPad.delete_all_chains()** _Built-In_
  > delete_all_chains( (DrumPad)arg1) -> None : Deletes all chains associated with a drum pad. This is equivalent to deleting a drum rack pad in Live. C++ signature :  void delete_all_chains(TPyHandle<ADrumGroupDevicePad>)
- **Live.DrumPad.DrumPad.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the drum pad.
- **Live.DrumPad.DrumPad.chains** _Property_RO_ — `get, observe`
  > Return const access to the list of chains in this drum pad.
- **Live.DrumPad.DrumPad.mute** _Property_ — `get, set, observe`
  > Mute/unmute the pad.
- **Live.DrumPad.DrumPad.name** _Property_RO_ — `get, observe`
  > Return const access to the drum pad's name. It depends on the contained chains.
- **Live.DrumPad.DrumPad.note** _Property_RO_ — `get`
  > Get the MIDI note of the drum pad.
- **Live.DrumPad.DrumPad.solo** _Property_ — `get, set, observe`
  > Solo/unsolo the pad.

## Live.Envelope


### Live.Envelope.Envelope

> This class represents an automation or modulation envelope in Live.

- **Live.Envelope.Envelope.create_event()** _Built-In_
  > create_event( (Envelope)arg1, (EnvelopeEvent)arg2) -> None : Creates a new event at the specified time with the given value and, optionally, control coefficients. C++ signature :  void create_event(TPyHandle<AAutomation> {lvalue},NApiHelpers::TEnvelopeEvent)
- **Live.Envelope.Envelope.delete_events_in_range()** _Built-In_
  > delete_events_in_range( (Envelope)arg1, (float)arg2, (float)arg3) -> None : Deletes the events in the specified time range. C++ signature :  void delete_events_in_range(TPyHandle<AAutomation> {lvalue},double,double)
- **Live.Envelope.Envelope.events_in_range()** _Built-In_
  > events_in_range( (Envelope)arg1, (float)arg2, (float)arg3) -> EnvelopeEventVector : Returns the events in the specified time range. C++ signature :  std::__1::vector<NApiHelpers::TEnvelopeEvent, std::__1::allocator<NApiHelpers::TEnvelopeEvent>> events_in_range(TPyHandle<AAutomation> {lvalue},double,double)
- **Live.Envelope.Envelope.insert_step()** _Built-In_
  > insert_step( (Envelope)arg1, (float)arg2, (float)arg3, (float)arg4) -> None : Given a start time, a step length and a value, creates a step in the envelope. C++ signature :  void insert_step(TPyHandle<AAutomation> {lvalue},double,double,double)
- **Live.Envelope.Envelope.value_at_time()** _Built-In_
  > value_at_time( (Envelope)arg1, (float)arg2) -> float : Returns the parameter value at the specified time. C++ signature :  double value_at_time(TPyHandle<AAutomation> {lvalue},double)
- **Live.Envelope.Envelope.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the envelope.
- **Live.Envelope.Envelope.parameter** _Property_RO_ — `get`
  > Read-only access to the parameter controlled by the envelope.

### Live.Envelope.EnvelopeEvent

> This is a class that represents an envelope event.

- **Live.Envelope.EnvelopeEvent.control_coefficients** _Property_ — `get, set`
- **Live.Envelope.EnvelopeEvent.time** _Property_ — `get, set`
- **Live.Envelope.EnvelopeEvent.value** _Property_ — `get, set`

### Live.Envelope.EnvelopeEventControlCoefficients

> This class represents the control coefficients of an envelope event.

- **Live.Envelope.EnvelopeEventControlCoefficients.x1** _Property_ — `get, set`
- **Live.Envelope.EnvelopeEventControlCoefficients.x2** _Property_ — `get, set`
- **Live.Envelope.EnvelopeEventControlCoefficients.y1** _Property_ — `get, set`
- **Live.Envelope.EnvelopeEventControlCoefficients.y2** _Property_ — `get, set`

### Live.Envelope.EnvelopeEventVector

> A container for holding envelope events.

- **Live.Envelope.EnvelopeEventVector.append()** _Built-In_
  > append( (EnvelopeEventVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<NApiHelpers::TEnvelopeEvent, std::__1::allocator<NApiHelpers::TEnvelopeEvent>> {lvalue},boost::python::api::object)
- **Live.Envelope.EnvelopeEventVector.extend()** _Built-In_
  > extend( (EnvelopeEventVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<NApiHelpers::TEnvelopeEvent, std::__1::allocator<NApiHelpers::TEnvelopeEvent>> {lvalue},boost::python::api::object)

## Live.Eq8Device


### Live.Eq8Device.EditMode

  - Enum (2): `a=a`, `b=b`

### Live.Eq8Device.Eq8Device

> This class represents an Eq8 device.

- **Live.Eq8Device.Eq8Device.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.Eq8Device.Eq8Device.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.Eq8Device.Eq8Device.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.Eq8Device.Eq8Device.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.Eq8Device.Eq8Device.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.Eq8Device.Eq8Device.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.Eq8Device.Eq8Device.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.Eq8Device.Eq8Device.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.Eq8Device.Eq8Device.edit_mode** _Property_ — `get, set, observe`
  > Access to Eq8's edit mode.
- **Live.Eq8Device.Eq8Device.global_mode** _Property_ — `get, set, observe`
  > Access to Eq8's global mode.
- **Live.Eq8Device.Eq8Device.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.Eq8Device.Eq8Device.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.Eq8Device.Eq8Device.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.Eq8Device.Eq8Device.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.Eq8Device.Eq8Device.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.Eq8Device.Eq8Device.oversample** _Property_ — `get, set, observe`
  > Access to Eq8's oversample value.
- **Live.Eq8Device.Eq8Device.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.Eq8Device.Eq8Device.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.Eq8Device.Eq8Device.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.Eq8Device.Eq8Device.View

> Representing the view aspects of an Eq8 device.

- **Live.Eq8Device.Eq8Device.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.Eq8Device.Eq8Device.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.
- **Live.Eq8Device.Eq8Device.View.selected_band** _Property_ — `get, set, observe`
  > Access to the selected filter band.

### Live.Eq8Device.GlobalMode

  - Enum (3): `stereo=stereo`, `left_right=left_right`, `mid_side=mid_side`

## Live.Groove


### Live.Groove.Base

  - Enum (7): `gb_four=gb_four`, `gb_eight=gb_eight`, `gb_eight_triplet=gb_eight_triplet`, `gb_sixteen=gb_sixteen`, `gb_sixteen_triplet=gb_sixteen_triplet`, `gb_thirtytwo=gb_thirtytwo`, `count=count`

### Live.Groove.Groove

> This class represents a groove in Live.

- **Live.Groove.Groove.base** _Property_ — `get, set`
  > Get/set the groove's base grid.
- **Live.Groove.Groove.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the groove.
- **Live.Groove.Groove.name** _Property_ — `get, set, observe`
  > Read/write/listen access to the groove's name
- **Live.Groove.Groove.quantization_amount** _Property_ — `get, set, observe`
  > Read/write/listen access to the groove's quantization amount.
- **Live.Groove.Groove.random_amount** _Property_ — `get, set, observe`
  > Read/write/listen access to the groove's random amount.
- **Live.Groove.Groove.timing_amount** _Property_ — `get, set, observe`
  > Read/write/listen access to the groove's timing amount.
- **Live.Groove.Groove.velocity_amount** _Property_ — `get, set, observe`
  > Read/write/listen access to the groove's velocity amount.

## Live.GroovePool


### Live.GroovePool.GroovePool

> This class represents the groove pool in Live.

- **Live.GroovePool.GroovePool.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the groove pool.
- **Live.GroovePool.GroovePool.grooves** _Property_RO_ — `get, observe`
  > Access to the list of grooves

## Live.HybridReverbDevice


### Live.HybridReverbDevice.HybridReverbDevice

> This class represents a Hybrid Reverb device.

- **Live.HybridReverbDevice.HybridReverbDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.HybridReverbDevice.HybridReverbDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.HybridReverbDevice.HybridReverbDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.HybridReverbDevice.HybridReverbDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.HybridReverbDevice.HybridReverbDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.HybridReverbDevice.HybridReverbDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.HybridReverbDevice.HybridReverbDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.HybridReverbDevice.HybridReverbDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.HybridReverbDevice.HybridReverbDevice.ir_attack_time** _Property_ — `get, set, observe`
  > Return the current IrAttackTime
- **Live.HybridReverbDevice.HybridReverbDevice.ir_category_index** _Property_ — `get, set, observe`
  > Return the current IR category index
- **Live.HybridReverbDevice.HybridReverbDevice.ir_category_list** _Property_RO_ — `get`
  > Return the current IR categories list
- **Live.HybridReverbDevice.HybridReverbDevice.ir_decay_time** _Property_ — `get, set, observe`
  > Return the current IrDecayTime
- **Live.HybridReverbDevice.HybridReverbDevice.ir_file_index** _Property_ — `get, set, observe`
  > Return the current IR file index
- **Live.HybridReverbDevice.HybridReverbDevice.ir_file_list** _Property_RO_ — `get, observe`
  > Return the current IR file list
- **Live.HybridReverbDevice.HybridReverbDevice.ir_size_factor** _Property_ — `get, set, observe`
  > Return the current IrSizeFactor
- **Live.HybridReverbDevice.HybridReverbDevice.ir_time_shaping_on** _Property_ — `get, set, observe`
  > Return the current IrTimeShapingOn
- **Live.HybridReverbDevice.HybridReverbDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.HybridReverbDevice.HybridReverbDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.HybridReverbDevice.HybridReverbDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.HybridReverbDevice.HybridReverbDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.HybridReverbDevice.HybridReverbDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.HybridReverbDevice.HybridReverbDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.HybridReverbDevice.HybridReverbDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.HybridReverbDevice.HybridReverbDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.HybridReverbDevice.HybridReverbDevice.View

> Representing the view aspects of a device.

- **Live.HybridReverbDevice.HybridReverbDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.HybridReverbDevice.HybridReverbDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.Licensing

- **Live.Licensing.authorization_clock_days_ahead()** _Built-In_
  > authorization_clock_days_ahead() -> int : Advances the current date by the number of days specified by _AuthClockDaysAhead C++ signature :  int authorization_clock_days_ahead()
- **Live.Licensing.get_authorization_page_url()** _Built-In_
  > get_authorization_page_url( (bool)reauthorize, (bool)is_trial) -> str : Retrieves the appopriate URL on ableton.com where the unser can initiate the authorization. C++ signature :  TString get_authorization_page_url(bool,bool)
- **Live.Licensing.get_purchase_live_url()** _Built-In_
  > get_purchase_live_url() -> str : Returns the environment-aware purchase URL for purchasing Live licenses C++ signature :  std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>> get_purchase_live_url()
- **Live.Licensing.get_services_url()** _Built-In_
  > get_services_url() -> str : Returns the URL against which service calls (e.g. for authorization) can be performed. C++ signature :  std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>> get_services_url()
- **Live.Licensing.get_unlock_dir()** _Built-In_
  > get_unlock_dir() -> tuple : Returns a tuple containing the unlock file directory and a flag indicating if the unlock file is in the system domain. C++ signature :  boost::python::tuple get_unlock_dir()
- **Live.Licensing.launch_web_browser()** _Built-In_
  > launch_web_browser( (str)url) -> None : Opens a web browser at the specified URL on the user's computer. C++ signature :  void launch_web_browser(std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>)

### Live.Licensing.ProgressDialog

> A modal dialog showing a message and a progress animation.

- **Live.Licensing.ProgressDialog.end_modal_loop()** _Built-In_
  > end_modal_loop( (ProgressDialog)arg1) -> None : C++ signature :  void end_modal_loop(AProgressDialog {lvalue})
- **Live.Licensing.ProgressDialog.run_in_modal_loop()** _Built-In_
  > run_in_modal_loop( (ProgressDialog)arg1) -> None : C++ signature :  void run_in_modal_loop(AProgressDialog {lvalue})
- **Live.Licensing.ProgressDialog.set_status_message()** _Built-In_
  > set_status_message( (object)arg1, (str)msg) -> None : C++ signature :  void set_status_message(TWeakPtr<AProgressDialog>,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>)

### Live.Licensing.PythonLicensingBridge

> Interface to the internal licensing services.

- **Live.Licensing.PythonLicensingBridge.authorize_with_sassafras()** _Built-In_
  > authorize_with_sassafras( (PythonLicensingBridge)arg1) -> None : C++ signature :  void authorize_with_sassafras(APythonLicensingBridge {lvalue})
- **Live.Licensing.PythonLicensingBridge.create_new_live_set()** _Built-In_
  > create_new_live_set( (PythonLicensingBridge)arg1) -> None : Creates a new live set and discards unsaved changes. C++ signature :  void create_new_live_set(APythonLicensingBridge {lvalue})
- **Live.Licensing.PythonLicensingBridge.deauthenticate_user()** _Built-In_
  > deauthenticate_user( (PythonLicensingBridge)arg1) -> None : Deletes the current session ID. C++ signature :  void deauthenticate_user(APythonLicensingBridge {lvalue})
- **Live.Licensing.PythonLicensingBridge.get_progress_dialog()** _Built-In_
  > get_progress_dialog( (PythonLicensingBridge)arg1) -> ProgressDialog : Retrieves an instance of ProgressDialog. C++ signature :  TWeakPtr<AProgressDialog> get_progress_dialog(APythonLicensingBridge {lvalue})
- **Live.Licensing.PythonLicensingBridge.get_session_id()** _Built-In_
  > get_session_id( (PythonLicensingBridge)arg1) -> str : Retrieve stored session ID. C++ signature :  std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>> get_session_id(APythonLicensingBridge {lvalue})
- **Live.Licensing.PythonLicensingBridge.get_startup_dialog()** _Built-In_
  > get_startup_dialog( (PythonLicensingBridge)arg1, (object)authorize_callable, (object)authorize_later_callable) -> StartupDialogServes as an entry point for the user to authorize Live on first launch. : Retrieves an instance of the startup dialog with the passed callables connected to its buttons. C++ signature :  TWeakPtr<AStartupDialog> get_startup_dialog(APythonLicensingBridge {lvalue},boost::python::api::object,boost::python::api::object)
- **Live.Licensing.PythonLicensingBridge.get_trial_time_left()** _Built-In_
  > get_trial_time_left( (PythonLicensingBridge)arg1) -> str : Returns remaining time on a trial as a formatted string. C++ signature :  TString get_trial_time_left(APythonLicensingBridge {lvalue})
- **Live.Licensing.PythonLicensingBridge.invoke_pack_installation_callback()** _Built-In_
  > invoke_pack_installation_callback( (PythonLicensingBridge)arg1) -> None : Call package installation callback. C++ signature :  void invoke_pack_installation_callback(APythonLicensingBridge {lvalue})
- **Live.Licensing.PythonLicensingBridge.load_and_convert_legacy_unlock_cfg()** _Built-In_
  > load_and_convert_legacy_unlock_cfg( (PythonLicensingBridge)arg1) -> dict : Loads the Unlock.cfg file and returns either an empty dict or one that can be converted to an UnlockData object. C++ signature :  boost::python::dict load_and_convert_legacy_unlock_cfg(APythonLicensingBridge {lvalue})
- **Live.Licensing.PythonLicensingBridge.process_license_response()** _Built-In_
  > process_license_response( (PythonLicensingBridge)arg1, (list)license_response_lines) -> UnlockStatus : Processes a list of strings, each representing a server response to a product authorization. C++ signature :  TUnlockStatus process_license_response(APythonLicensingBridge {lvalue},boost::python::list)
- **Live.Licensing.PythonLicensingBridge.process_trial_response()** _Built-In_
  > process_trial_response( (PythonLicensingBridge)arg1, (str)trial_response_line) -> bool : Process the server's response to a Trial authorization. C++ signature :  bool process_trial_response(APythonLicensingBridge {lvalue},std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>)
- **Live.Licensing.PythonLicensingBridge.request_exit()** _Built-In_
  > request_exit( (PythonLicensingBridge)arg1 [, (int)exit_code=0]) -> None : C++ signature :  void request_exit(APythonLicensingBridge {lvalue} [,int=0])
- **Live.Licensing.PythonLicensingBridge.save_current_set()** _Built-In_
  > save_current_set( (PythonLicensingBridge)arg1) -> None : Saves the current Live session. C++ signature :  void save_current_set(APythonLicensingBridge {lvalue})
- **Live.Licensing.PythonLicensingBridge.set_network_timer()** _Built-In_
  > set_network_timer( (PythonLicensingBridge)arg1, (object)callback, (int)interval_in_ms) -> None : Starts or stops a timer meant for driving network operations. Pass None as callback to stop the timer. If any callback invocation raises an exception, the timer is stopped. C++ signature :  void set_network_timer(APythonLicensingBridge {lvalue},boost::python::api::object,int)
- **Live.Licensing.PythonLicensingBridge.store_session_identifiers()** _Built-In_
  > store_session_identifiers( (PythonLicensingBridge)arg1, (str)session_id, (str)external_session_id) -> None : Securely stores the user's session Identifiers (aka credentials). C++ signature :  void store_session_identifiers(APythonLicensingBridge {lvalue},std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>>)
- **Live.Licensing.PythonLicensingBridge.base_product_id** _Property_RO_ — `get`
  > Returns Live's current base product ID.
- **Live.Licensing.PythonLicensingBridge.in_sassafras_mode** _Property_RO_ — `get`
- **Live.Licensing.PythonLicensingBridge.license_must_match_variant** _Property_RO_ — `get`
  > Returns a bool indicating if we require the license information returned by the server to match the variant of Live.
- **Live.Licensing.PythonLicensingBridge.random_number_for_trial_authorization** _Property_RO_ — `get`
  > Returns the integer to send along with the Trial authorization request. This same integer will be checked for in `process_trial_response` (and then changed).
- **Live.Licensing.PythonLicensingBridge.set_has_unsaved_changes** _Property_RO_ — `get`
  > Returns true if the set has unsaved changes.

#### Live.Licensing.StartupDialogServes as an entry point for the user to authorize Live on first launch.

- **Live.Licensing.StartupDialogServes as an entry point for the user to authorize Live on first launch..end_modal_loop()** _Built-In_
  > end_modal_loop( (StartupDialogServes as an entry point for the user to authorize Live on first launch.)arg1) -> None : C++ signature :  void end_modal_loop(AStartupDialog {lvalue})
- **Live.Licensing.StartupDialogServes as an entry point for the user to authorize Live on first launch..run_in_modal_loop()** _Built-In_
  > run_in_modal_loop( (StartupDialogServes as an entry point for the user to authorize Live on first launch.)arg1, (bool)show_only_offline_auth_instructions) -> None : C++ signature :  void run_in_modal_loop(AStartupDialog {lvalue},bool)
- **Live.Licensing.StartupDialogServes as an entry point for the user to authorize Live on first launch..set_notification_message()** _Built-In_
  > set_notification_message( (StartupDialogServes as an entry point for the user to authorize Live on first launch.)arg1, (object)notification_text, (bool)show_progress_bar) -> None : C++ signature :  void set_notification_message(AStartupDialog {lvalue},TString,bool)

### Live.Licensing.TrialContext

  - Enum (3): `SAVE=SAVE`, `FORCE_UPDATE=FORCE_UPDATE`, `STARTUP=STARTUP`

### Live.Licensing.UnlockStatus

> Returns relevant information after unlock

- **Live.Licensing.UnlockStatus.authorization_deactivated** _Property_RO_ — `get`
- **Live.Licensing.UnlockStatus.authorization_expired** _Property_RO_ — `get`
- **Live.Licensing.UnlockStatus.has_max_unlock_products** _Property_RO_ — `get`
- **Live.Licensing.UnlockStatus.temp_demo_mode** _Property_RO_ — `get`
- **Live.Licensing.UnlockStatus.time_limited** _Property_RO_ — `get`
- **Live.Licensing.UnlockStatus.unlock_error** _Property_RO_ — `get`
- **Live.Licensing.UnlockStatus.unlocked** _Property_RO_ — `get`

## Live.Listener


### Live.Listener.ListenerHandle

> This class represents a Python listener when connected to a Live property.

- **Live.Listener.ListenerHandle.disconnect()** _Built-In_
  > disconnect( (ListenerHandle)arg1) -> None : Disconnects the listener from its property C++ signature :  void disconnect(LPythonRemote {lvalue})
- **Live.Listener.ListenerHandle.listener_func** _Property_RO_ — `get`
  > Returns the original function
- **Live.Listener.ListenerHandle.listener_self** _Property_RO_ — `get`
  > Returns the weak reference to original self, if it was a bound method
- **Live.Listener.ListenerHandle.name** _Property_RO_ — `get`
  > Prints the name of the property that this listener is connected to

### Live.Listener.ListenerVector

> A read only container for accessing a list of listeners.

- **Live.Listener.ListenerVector.append()** _Built-In_
  > append( (ListenerVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<TWeakPtr<LPythonRemote>, std::__1::allocator<TWeakPtr<LPythonRemote>>> {lvalue},boost::python::api::object)
- **Live.Listener.ListenerVector.extend()** _Built-In_
  > extend( (ListenerVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<TWeakPtr<LPythonRemote>, std::__1::allocator<TWeakPtr<LPythonRemote>>> {lvalue},boost::python::api::object)

## Live.LomObject


### Live.LomObject.LomObject

> this is the base class for an object that is accessible via the LOM


## Live.LooperDevice


### Live.LooperDevice.LooperDevice

> This class represents a Looper device.

- **Live.LooperDevice.LooperDevice.clear()** _Built-In_
  > clear( (LooperDevice)arg1) -> None : Erase Looper's recorded content. C++ signature :  void clear(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.double_length()** _Built-In_
  > double_length( (LooperDevice)arg1) -> None : Double the length of Looper's buffer. C++ signature :  void double_length(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.double_speed()** _Built-In_
  > double_speed( (LooperDevice)arg1) -> None : Double the speed of Looper's playback. C++ signature :  void double_speed(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.export_to_clip_slot()** _Built-In_
  > export_to_clip_slot( (LooperDevice)arg1, (ClipSlot)arg2) -> None : Export Looper's content to a Session Clip Slot. C++ signature :  void export_to_clip_slot(TLooperDevicePyHandle,TPyHandle<AGroupAndClipSlotBase>)
- **Live.LooperDevice.LooperDevice.half_length()** _Built-In_
  > half_length( (LooperDevice)arg1) -> None : Halve the length of Looper's buffer. C++ signature :  void half_length(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.half_speed()** _Built-In_
  > half_speed( (LooperDevice)arg1) -> None : Halve the speed of Looper's playback. C++ signature :  void half_speed(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.overdub()** _Built-In_
  > overdub( (LooperDevice)arg1) -> None : Play back while adding additional layers of incoming audio. C++ signature :  void overdub(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.play()** _Built-In_
  > play( (LooperDevice)arg1) -> None : Play back without overdubbing. C++ signature :  void play(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.record()** _Built-In_
  > record( (LooperDevice)arg1) -> None : Record incoming audio. C++ signature :  void record(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.LooperDevice.LooperDevice.stop()** _Built-In_
  > stop( (LooperDevice)arg1) -> None : Stop Looper's playback. C++ signature :  void stop(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.LooperDevice.LooperDevice.undo()** _Built-In_
  > undo( (LooperDevice)arg1) -> None : Erase everything that was recorded since the last time Overdub was enabled. Calling a second time will restore the material erased by the previous undooperation. C++ signature :  void undo(TLooperDevicePyHandle)
- **Live.LooperDevice.LooperDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.LooperDevice.LooperDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.LooperDevice.LooperDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.LooperDevice.LooperDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.LooperDevice.LooperDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.LooperDevice.LooperDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.LooperDevice.LooperDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.LooperDevice.LooperDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.LooperDevice.LooperDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.LooperDevice.LooperDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.LooperDevice.LooperDevice.loop_length** _Property_RO_ — `get, observe`
  > The length of Looper's buffer.
- **Live.LooperDevice.LooperDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.LooperDevice.LooperDevice.overdub_after_record** _Property_ — `get, set, observe`
  > If true, Looper will switch to overdub after recording, when recording a fixed number of bars. Otherwise, the switch will be to playback without overdubbing.
- **Live.LooperDevice.LooperDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.LooperDevice.LooperDevice.record_length_index** _Property_ — `get, set, observe`
  > Access to the Record Length chooser entry index.
- **Live.LooperDevice.LooperDevice.record_length_list** _Property_RO_ — `get`
  > Read-only access to the list of Record Length chooser entry strings.
- **Live.LooperDevice.LooperDevice.tempo** _Property_RO_ — `get, observe`
  > The tempo of Looper's buffer.
- **Live.LooperDevice.LooperDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.LooperDevice.LooperDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.LooperDevice.LooperDevice.View

> Representing the view aspects of a device.

- **Live.LooperDevice.LooperDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.LooperDevice.LooperDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.MaxDevice


### Live.MaxDevice.MaxDevice

> This class represents a Max for Live device.

- **Live.MaxDevice.MaxDevice.get_bank_count()** _Built-In_
  > get_bank_count( (MaxDevice)arg1) -> int : Get the number of parameter banks. This is related to hardware control surfaces. C++ signature :  int get_bank_count(TMaxDevicePyHandle)
- **Live.MaxDevice.MaxDevice.get_bank_name()** _Built-In_
  > get_bank_name( (MaxDevice)arg1, (int)arg2) -> str : Get the name of a parameter bank given by index. This is related to hardware control surfaces. C++ signature :  TString get_bank_name(TMaxDevicePyHandle,int)
- **Live.MaxDevice.MaxDevice.get_bank_parameters()** _Built-In_
  > get_bank_parameters( (MaxDevice)arg1, (int)arg2) -> list : Get the indices of parameters of the given bank index. Empty slots are marked as -1. Bank index -1 refers to the best-of bank. This function is related to hardware control surfaces. C++ signature :  boost::python::list get_bank_parameters(TMaxDevicePyHandle,int)
- **Live.MaxDevice.MaxDevice.get_value_item_icons()** _Built-In_
  > get_value_item_icons( (MaxDevice)arg1, (DeviceParameter)arg2) -> list : Get a list of icon identifier strings for a list parameter's values.An empty string is given where no icon should be displayed.An empty list is given when no icons should be displayed.This is related to hardware control surfaces. C++ signature :  boost::python::list get_value_item_icons(TMaxDevicePyHandle,TPyHandle<ATimeableValue>)
- **Live.MaxDevice.MaxDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.MaxDevice.MaxDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.MaxDevice.MaxDevice.audio_inputs** _Property_RO_ — `get, observe`
  > Const access to a list of all audio inputs of the device.
- **Live.MaxDevice.MaxDevice.audio_outputs** _Property_RO_ — `get, observe`
  > Const access to a list of all audio outputs of the device.
- **Live.MaxDevice.MaxDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.MaxDevice.MaxDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.MaxDevice.MaxDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.MaxDevice.MaxDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.MaxDevice.MaxDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.MaxDevice.MaxDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.MaxDevice.MaxDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.MaxDevice.MaxDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.MaxDevice.MaxDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.MaxDevice.MaxDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.MaxDevice.MaxDevice.midi_inputs** _Property_RO_ — `get, observe`
  > Const access to a list of all midi outputs of the device.
- **Live.MaxDevice.MaxDevice.midi_outputs** _Property_RO_ — `get, observe`
  > Const access to a list of all midi outputs of the device.
- **Live.MaxDevice.MaxDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.MaxDevice.MaxDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.MaxDevice.MaxDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.MaxDevice.MaxDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.MaxDevice.MaxDevice.View

> Representing the view aspects of a device.

- **Live.MaxDevice.MaxDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.MaxDevice.MaxDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.MeldDevice


### Live.MeldDevice.MeldDevice

> This class represents a Meld device.

- **Live.MeldDevice.MeldDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.MeldDevice.MeldDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.MeldDevice.MeldDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.MeldDevice.MeldDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.MeldDevice.MeldDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.MeldDevice.MeldDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.MeldDevice.MeldDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.MeldDevice.MeldDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.MeldDevice.MeldDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.MeldDevice.MeldDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.MeldDevice.MeldDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.MeldDevice.MeldDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.MeldDevice.MeldDevice.mono_poly** _Property_ — `get, set, observe`
  > Returns the mode of Polyphony
- **Live.MeldDevice.MeldDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.MeldDevice.MeldDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.MeldDevice.MeldDevice.poly_voices** _Property_ — `get, set, observe`
  > Return the Poly Voice count
- **Live.MeldDevice.MeldDevice.selected_engine** _Property_ — `get, set, observe`
  > Return what Voice Engine is selected
- **Live.MeldDevice.MeldDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.MeldDevice.MeldDevice.unison_voices** _Property_ — `get, set, observe`
  > Return the Unison Voice count
- **Live.MeldDevice.MeldDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.MeldDevice.MeldDevice.View

> Representing the view aspects of a device.

- **Live.MeldDevice.MeldDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.MeldDevice.MeldDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.MidiMap

- **Live.MidiMap.forward_midi_cc()** _Built-In_
  > forward_midi_cc( (int)arg1, (int)arg2, (int)arg3, (int)arg4 [, (bool)ShouldConsumeEvent=True]) -> bool : C++ signature :  bool forward_midi_cc(unsigned int,unsigned int,int,int [,bool=True])
- **Live.MidiMap.forward_midi_note()** _Built-In_
  > forward_midi_note( (int)arg1, (int)arg2, (int)arg3, (int)arg4 [, (bool)ShouldConsumeEvent=True]) -> bool : C++ signature :  bool forward_midi_note(unsigned int,unsigned int,int,int [,bool=True])
- **Live.MidiMap.forward_midi_pitchbend()** _Built-In_
  > forward_midi_pitchbend( (int)arg1, (int)arg2, (int)arg3) -> bool : C++ signature :  bool forward_midi_pitchbend(unsigned int,unsigned int,int)
- **Live.MidiMap.map_midi_cc()** _Built-In_
  > map_midi_cc( (int)midi_map_handle, (DeviceParameter)parameter, (int)midi_channel, (int)controller_number, (MapMode)map_mode, (bool)avoid_takeover [, (float)sensitivity=1.0]) -> bool : C++ signature :  bool map_midi_cc(unsigned int,TPyHandle<ATimeableValue>,int,int,NRemoteMapperTypes::TControllerMapMode,bool [,float=1.0])
- **Live.MidiMap.map_midi_cc_with_feedback_map()** _Built-In_
  > map_midi_cc_with_feedback_map( (int)midi_map_handle, (DeviceParameter)parameter, (int)midi_channel, (int)controller_number, (MapMode)map_mode, (CCFeedbackRule)feedback_rule, (bool)avoid_takeover [, (float)sensitivity=1.0]) -> bool : C++ signature :  bool map_midi_cc_with_feedback_map(unsigned int,TPyHandle<ATimeableValue>,int,int,NRemoteMapperTypes::TControllerMapMode,NPythonMidiMap::TCCFeedbackRule,bool [,float=1.0])
- **Live.MidiMap.map_midi_note()** _Built-In_
  > map_midi_note( (int)arg1, (DeviceParameter)arg2, (int)arg3, (int)arg4) -> bool : C++ signature :  bool map_midi_note(unsigned int,TPyHandle<ATimeableValue>,int,int)
- **Live.MidiMap.map_midi_note_with_feedback_map()** _Built-In_
  > map_midi_note_with_feedback_map( (int)arg1, (DeviceParameter)arg2, (int)arg3, (int)arg4, (NoteFeedbackRule)arg5) -> bool : C++ signature :  bool map_midi_note_with_feedback_map(unsigned int,TPyHandle<ATimeableValue>,int,int,NPythonMidiMap::TNoteFeedbackRule)
- **Live.MidiMap.map_midi_pitchbend()** _Built-In_
  > map_midi_pitchbend( (int)arg1, (DeviceParameter)arg2, (int)arg3, (bool)arg4) -> bool : C++ signature :  bool map_midi_pitchbend(unsigned int,TPyHandle<ATimeableValue>,int,bool)
- **Live.MidiMap.map_midi_pitchbend_with_feedback_map()** _Built-In_
  > map_midi_pitchbend_with_feedback_map( (int)arg1, (DeviceParameter)arg2, (int)arg3, (PitchBendFeedbackRule)arg4, (bool)arg5) -> bool : C++ signature :  bool map_midi_pitchbend_with_feedback_map(unsigned int,TPyHandle<ATimeableValue>,int,NPythonMidiMap::TPitchBendFeedbackRule,bool)
- **Live.MidiMap.send_feedback_for_parameter()** _Built-In_
  > send_feedback_for_parameter( (int)arg1, (DeviceParameter)arg2) -> None : C++ signature :  void send_feedback_for_parameter(unsigned int,TPyHandle<ATimeableValue>)

### Live.MidiMap.CCFeedbackRule

> Structure to define feedback properties of MIDI mappings.

- **Live.MidiMap.CCFeedbackRule.cc_no** _Property_ — `get, set`
- **Live.MidiMap.CCFeedbackRule.cc_value_map** _Property_ — `get, set`
- **Live.MidiMap.CCFeedbackRule.channel** _Property_ — `get, set`
- **Live.MidiMap.CCFeedbackRule.delay_in_ms** _Property_ — `get, set`
- **Live.MidiMap.CCFeedbackRule.enabled** _Property_ — `get, set`

### Live.MidiMap.MapMode

  - Enum (10): `absolute=absolute`, `relative_signed_bit=relative_signed_bit`, `relative_binary_offset=relative_binary_offset`, `relative_two_compliment=relative_two_compliment`, `relative_signed_bit2=relative_signed_bit2`, `absolute_14_bit=absolute_14_bit`, `relative_smooth_signed_bit=relative_smooth_signed_bit`, `relative_smooth_binary_offset=relative_smooth_binary_offset`, `relative_smooth_two_compliment=relative_smooth_two_compliment`, `relative_smooth_signed_bit2=relative_smooth_signed_bit2`

### Live.MidiMap.NoteFeedbackRule

> Structure to define feedback properties of MIDI mappings.

- **Live.MidiMap.NoteFeedbackRule.channel** _Property_ — `get, set`
- **Live.MidiMap.NoteFeedbackRule.delay_in_ms** _Property_ — `get, set`
- **Live.MidiMap.NoteFeedbackRule.enabled** _Property_ — `get, set`
- **Live.MidiMap.NoteFeedbackRule.note_no** _Property_ — `get, set`
- **Live.MidiMap.NoteFeedbackRule.vel_map** _Property_ — `get, set`

### Live.MidiMap.PitchBendFeedbackRule

> Structure to define feedback properties of MIDI mappings.

- **Live.MidiMap.PitchBendFeedbackRule.channel** _Property_ — `get, set`
- **Live.MidiMap.PitchBendFeedbackRule.delay_in_ms** _Property_ — `get, set`
- **Live.MidiMap.PitchBendFeedbackRule.enabled** _Property_ — `get, set`
- **Live.MidiMap.PitchBendFeedbackRule.value_pair_map** _Property_ — `get, set`

## Live.MixerDevice


### Live.MixerDevice.MixerDevice

> This class represents a Mixer Device in Live, which gives youaccess to the Volume and Panning properties of a Track.

- **Live.MixerDevice.MixerDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the mixer device.
- **Live.MixerDevice.MixerDevice.crossfade_assign** _Property_ — `get, set, observe`
  > Player- and ReturnTracks only: Access to the Track's Crossfade Assign State.
- **Live.MixerDevice.MixerDevice.crossfader** _Property_RO_ — `get`
  > MainTrack only: Const access to the Crossfader.
- **Live.MixerDevice.MixerDevice.cue_volume** _Property_RO_ — `get`
  > MainTrack only: Const access to the Cue Volume Parameter.
- **Live.MixerDevice.MixerDevice.left_split_stereo** _Property_RO_ — `get`
  > Const access to the Track's Left Split Stereo Panning Device Parameter.
- **Live.MixerDevice.MixerDevice.panning** _Property_RO_ — `get`
  > Const access to the Tracks Panning Device Parameter.
- **Live.MixerDevice.MixerDevice.panning_mode** _Property_ — `get, set, observe`
  > Access to the Track's Panning Mode.
- **Live.MixerDevice.MixerDevice.right_split_stereo** _Property_RO_ — `get`
  > Const access to the Track's Right Split Stereo Panning Device Parameter.
- **Live.MixerDevice.MixerDevice.sends** _Property_RO_ — `get, observe`
  > Const access to the Tracks list of Send Amount Device Parameters.
- **Live.MixerDevice.MixerDevice.song_tempo** _Property_RO_ — `get`
  > MainTrack only: Const access to the Song's Tempo.
- **Live.MixerDevice.MixerDevice.track_activator** _Property_RO_ — `get`
  > Const access to the Tracks Activator Device Parameter.
- **Live.MixerDevice.MixerDevice.volume** _Property_RO_ — `get`
  > Const access to the Tracks Volume Device Parameter.

#### Live.MixerDevice.MixerDevice.crossfade_assignments

  - Enum (3): `A=A`, `NONE=NONE`, `B=B`

#### Live.MixerDevice.MixerDevice.panning_modes

  - Enum (2): `stereo=stereo`, `stereo_split=stereo_split`

## Live.PluginDevice


### Live.PluginDevice.PluginDevice

> This class represents a plugin device.

- **Live.PluginDevice.PluginDevice.get_parameter_names()** _Built-In_
  > get_parameter_names( (PluginDevice)arg1 [, (int)begin=0 [, (int)end=-1]]) -> StringVector : Get the range of plugin parameter names, bound by begin and end. If end is smaller than 0 it is interpreted as the parameter count.  C++ signature :  std::__1::vector<TString, std::__1::allocator<TString>> get_parameter_names(TPluginDevicePyHandle [,int=0 [,int=-1]])
- **Live.PluginDevice.PluginDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.PluginDevice.PluginDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.PluginDevice.PluginDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.PluginDevice.PluginDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.PluginDevice.PluginDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.PluginDevice.PluginDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.PluginDevice.PluginDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.PluginDevice.PluginDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.PluginDevice.PluginDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.PluginDevice.PluginDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.PluginDevice.PluginDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.PluginDevice.PluginDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.PluginDevice.PluginDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.PluginDevice.PluginDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.PluginDevice.PluginDevice.presets** _Property_RO_ — `get, observe`
  > Get the list of presets the plugin offers.
- **Live.PluginDevice.PluginDevice.selected_preset_index** _Property_ — `get, set, observe`
  > Access to the index of the currently selected preset.
- **Live.PluginDevice.PluginDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.PluginDevice.PluginDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.PluginDevice.PluginDevice.View

> Representing the view aspects of a device.

- **Live.PluginDevice.PluginDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.PluginDevice.PluginDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.RackDevice


### Live.RackDevice.RackDevice

> This class represents a Rack device.

- **Live.RackDevice.RackDevice.add_macro()** _Built-In_
  > add_macro( (RackDevice)arg1) -> None : Increases the number of visible macro controls in the rack. Throws an exception if the maximum number of macro controls is reached. C++ signature :  void add_macro(TRackDevicePyHandle)
- **Live.RackDevice.RackDevice.copy_pad()** _Built-In_
  > copy_pad( (RackDevice)arg1, (int)arg2, (int)arg3) -> None : Copies all contents of a drum pad from a source pad into a destination pad. copy_pad(source_index, destination_index) where source_index and destination_index correspond to the note number/index of the drum pad in a drum rack. Throws an exception when the source pad is empty, or when the source or destination indices are not between 0 - 127. C++ signature :  void copy_pad(TRackDevicePyHandle,int,int)
- **Live.RackDevice.RackDevice.delete_selected_variation()** _Built-In_
  > delete_selected_variation( (Device)arg1) -> None : Deletes the currently selected macro variation.Does nothing if there is no selected variation. C++ signature :  void delete_selected_variation(TPyHandle<ADevice>)
- **Live.RackDevice.RackDevice.insert_chain()** _Built-In_
  > insert_chain( (RackDevice)arg1 [, (int)Index=-1]) -> LomObject : Inserts a new chain, either at the specified index or, if not index was specified, at the end of the chain sequence. C++ signature :  TWeakPtr<TPyHandleBase> insert_chain(TRackDevicePyHandle [,int=-1])
- **Live.RackDevice.RackDevice.randomize_macros()** _Built-In_
  > randomize_macros( (RackDevice)arg1) -> None : Randomizes the values for all macro controls not excluded from randomization. C++ signature :  void randomize_macros(TRackDevicePyHandle)
- **Live.RackDevice.RackDevice.recall_last_used_variation()** _Built-In_
  > recall_last_used_variation( (Device)arg1) -> None : Recalls the macro variation that was recalled most recently.Does nothing if no variation has been recalled yet. C++ signature :  void recall_last_used_variation(TPyHandle<ADevice>)
- **Live.RackDevice.RackDevice.recall_selected_variation()** _Built-In_
  > recall_selected_variation( (Device)arg1) -> None : Recalls the currently selected macro variation.Does nothing if there are no variations. C++ signature :  void recall_selected_variation(TPyHandle<ADevice>)
- **Live.RackDevice.RackDevice.remove_macro()** _Built-In_
  > remove_macro( (RackDevice)arg1) -> None : Decreases the number of visible macro controls in the rack. Throws an exception if the minimum number of macro controls is reached. C++ signature :  void remove_macro(TRackDevicePyHandle)
- **Live.RackDevice.RackDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.RackDevice.RackDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.RackDevice.RackDevice.store_variation()** _Built-In_
  > store_variation( (Device)arg1) -> None : Stores a new variation of the values of all currently mapped macros C++ signature :  void store_variation(TPyHandle<ADevice>)
- **Live.RackDevice.RackDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.RackDevice.RackDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.RackDevice.RackDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.RackDevice.RackDevice.can_show_chains** _Property_RO_ — `get`
  > return True, if this Rack contains a rack instrument device that is capable of showing its chains in session view.
- **Live.RackDevice.RackDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.RackDevice.RackDevice.chain_selector** _Property_RO_ — `get`
  > Const access to the chain selector parameter.
- **Live.RackDevice.RackDevice.chains** _Property_RO_ — `get, observe`
  > Return const access to the list of chains in this device. Throws an exception if can_have_chains is false.
- **Live.RackDevice.RackDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.RackDevice.RackDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.RackDevice.RackDevice.drum_pads** _Property_RO_ — `get, observe`
  > Return const access to the list of drum pads in this device. Throws an exception if can_have_drum_pads is false.
- **Live.RackDevice.RackDevice.has_drum_pads** _Property_RO_ — `get, observe`
  > Returns true if the device is a drum rack which has drum pads. Throws an exception if can_have_drum_pads is false.
- **Live.RackDevice.RackDevice.has_macro_mappings** _Property_RO_ — `get, observe`
  > Returns true if any of the rack's macros are mapped to a parameter.
- **Live.RackDevice.RackDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.RackDevice.RackDevice.is_showing_chains** _Property_ — `get, set, observe`
  > Returns True, if it is showing chains.
- **Live.RackDevice.RackDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.RackDevice.RackDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.RackDevice.RackDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.RackDevice.RackDevice.macros_mapped** _Property_RO_ — `get, observe`
  > A list of booleans, one for each macro parameter, which is True iffthat macro is mapped to something
- **Live.RackDevice.RackDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.RackDevice.RackDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.RackDevice.RackDevice.return_chains** _Property_RO_ — `get, observe`
  > Return const access to the list of return chains in this device. Throws an exception if can_have_chains is false.
- **Live.RackDevice.RackDevice.selected_variation_index** _Property_ — `get, set`
  > Access to the index of the currently selected macro variation.Throws an exception if the index is out of range.
- **Live.RackDevice.RackDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.RackDevice.RackDevice.variation_count** _Property_RO_ — `get, observe`
  > Access to the number of macro variations currently stored.
- **Live.RackDevice.RackDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.
- **Live.RackDevice.RackDevice.visible_drum_pads** _Property_RO_ — `get, observe`
  > Return const access to the list of visible drum pads in this device. Throws an exception if can_have_drum_pads is false.
- **Live.RackDevice.RackDevice.visible_macro_count** _Property_RO_ — `get, observe`
  > Access to the number of macros that are currently visible.

#### Live.RackDevice.RackDevice.View

> Representing the view aspects of a rack device.

- **Live.RackDevice.RackDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.RackDevice.RackDevice.View.drum_pads_scroll_position** _Property_ — `get, set, observe`
  > Access to the index of the lowest visible row of pads. Throws an exception if can_have_drum_pads is false.
- **Live.RackDevice.RackDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.
- **Live.RackDevice.RackDevice.View.is_showing_chain_devices** _Property_ — `get, set, observe`
  > Return whether the devices in the currently selected chain are visible. Throws an exception if can_have_chains is false.
- **Live.RackDevice.RackDevice.View.selected_chain** _Property_ — `get, set, observe`
  > Return access to the currently selected chain.
- **Live.RackDevice.RackDevice.View.selected_drum_pad** _Property_ — `get, set, observe`
  > Return access to the currently selected drum pad. Throws an exception if can_have_drum_pads is false.

## Live.RoarDevice


### Live.RoarDevice.RoarDevice

> This class represents a Roar device.

- **Live.RoarDevice.RoarDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.RoarDevice.RoarDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.RoarDevice.RoarDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.RoarDevice.RoarDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.RoarDevice.RoarDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.RoarDevice.RoarDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.RoarDevice.RoarDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.RoarDevice.RoarDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.RoarDevice.RoarDevice.env_listen** _Property_ — `get, set, observe`
  > Return the Envelope Input Listen toggle state
- **Live.RoarDevice.RoarDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.RoarDevice.RoarDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.RoarDevice.RoarDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.RoarDevice.RoarDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.RoarDevice.RoarDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.RoarDevice.RoarDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.RoarDevice.RoarDevice.routing_mode_index** _Property_ — `get, set, observe`
  > Return the routing mode index
- **Live.RoarDevice.RoarDevice.routing_mode_list** _Property_RO_ — `get`
  > Return the routing mode list
- **Live.RoarDevice.RoarDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.RoarDevice.RoarDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.RoarDevice.RoarDevice.View

> Representing the view aspects of a device.

- **Live.RoarDevice.RoarDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.RoarDevice.RoarDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.Sample


### Live.Sample.Sample

> This class represents a sample file loaded into a Simpler instance.

- **Live.Sample.Sample.beat_to_sample_time()** _Built-In_
  > beat_to_sample_time( (Sample)self, (float)beat_time) -> float : Converts the given beat time to sample time. Raises an error if the sample is not warped. C++ signature :  double beat_to_sample_time(TPyHandle<AMultiSamplePart>,double)
- **Live.Sample.Sample.clear_slices()** _Built-In_
  > clear_slices( (Sample)self) -> None : Clears all slices created in Simpler's manual mode. C++ signature :  void clear_slices(TPyHandle<AMultiSamplePart>)
- **Live.Sample.Sample.gain_display_string()** _Built-In_
  > gain_display_string( (Sample)self) -> str : Get the gain's display value as a string. C++ signature :  TString gain_display_string(TPyHandle<AMultiSamplePart>)
- **Live.Sample.Sample.insert_slice()** _Built-In_
  > insert_slice( (Sample)self, (int)slice_time) -> None : Add a slice point at the provided time if there is none. C++ signature :  void insert_slice(TPyHandle<AMultiSamplePart>,int)
- **Live.Sample.Sample.move_slice()** _Built-In_
  > move_slice( (Sample)self, (int)old_time, (int)new_time) -> int : Move the slice point at the provided time. C++ signature :  int move_slice(TPyHandle<AMultiSamplePart>,int,int)
- **Live.Sample.Sample.remove_slice()** _Built-In_
  > remove_slice( (Sample)self, (int)slice_time) -> None : Remove the slice point at the provided time if there is one. C++ signature :  void remove_slice(TPyHandle<AMultiSamplePart>,int)
- **Live.Sample.Sample.reset_slices()** _Built-In_
  > reset_slices( (Sample)self) -> None : Resets all edited slices to their original positions. C++ signature :  void reset_slices(TPyHandle<AMultiSamplePart>)
- **Live.Sample.Sample.sample_to_beat_time()** _Built-In_
  > sample_to_beat_time( (Sample)self, (float)sample_time) -> float : Converts the given sample time to beat time. Raises an error if the sample is not warped. C++ signature :  double sample_to_beat_time(TPyHandle<AMultiSamplePart>,double)
- **Live.Sample.Sample.beats_granulation_resolution** _Property_ — `get, set, observe`
  > Access to the Granulation Resolution parameter in Beats Warp Mode.
- **Live.Sample.Sample.beats_transient_envelope** _Property_ — `get, set, observe`
  > Access to the Transient Envelope parameter in Beats Warp Mode.
- **Live.Sample.Sample.beats_transient_loop_mode** _Property_ — `get, set, observe`
  > Access to the Transient Loop Mode parameter in Beats Warp Mode.
- **Live.Sample.Sample.canonical_parent** _Property_RO_ — `get`
  > Access to the sample's canonical parent.
- **Live.Sample.Sample.complex_pro_envelope** _Property_ — `get, set, observe`
  > Access to the Envelope parameter in Complex Pro Mode.
- **Live.Sample.Sample.complex_pro_formants** _Property_ — `get, set, observe`
  > Access to the Formants parameter in Complex Pro Warp Mode.
- **Live.Sample.Sample.end_marker** _Property_ — `get, set, observe`
  > Access to the position of the sample's end marker.
- **Live.Sample.Sample.file_path** _Property_RO_ — `get, observe`
  > Get the path of the sample file.
- **Live.Sample.Sample.gain** _Property_ — `get, set, observe`
  > Access to the sample gain.
- **Live.Sample.Sample.length** _Property_RO_ — `get`
  > Get the length of the sample file in sample frames.
- **Live.Sample.Sample.sample_rate** _Property_RO_ — `get`
  > Access to the audio sample rate of the sample.
- **Live.Sample.Sample.slices** _Property_RO_ — `get, observe`
  > Access to the list of slice points in sample time in the sample.
- **Live.Sample.Sample.slicing_beat_division** _Property_ — `get, set, observe`
  > Access to sample's slicing step size.
- **Live.Sample.Sample.slicing_region_count** _Property_ — `get, set, observe`
  > Access to sample's slicing split count.
- **Live.Sample.Sample.slicing_sensitivity** _Property_ — `get, set, observe`
  > Access to sample's slicing sensitivity whose sensitivity is in between 0.0 and 1.0.The higher the sensitivity, the more slices will be available.
- **Live.Sample.Sample.slicing_style** _Property_ — `get, set, observe`
  > Access to sample's slicing style.
- **Live.Sample.Sample.start_marker** _Property_ — `get, set, observe`
  > Access to the position of the sample's start marker.
- **Live.Sample.Sample.texture_flux** _Property_ — `get, set, observe`
  > Access to the Flux parameter in Texture Warp Mode.
- **Live.Sample.Sample.texture_grain_size** _Property_ — `get, set, observe`
  > Access to the Grain Size parameter in Texture Warp Mode.
- **Live.Sample.Sample.tones_grain_size** _Property_ — `get, set, observe`
  > Access to the Grain Size parameter in Tones Warp Mode.
- **Live.Sample.Sample.warp_markers** _Property_RO_ — `get, observe`
  > Get the warp markers for this sample.
- **Live.Sample.Sample.warp_mode** _Property_ — `get, set, observe`
  > Access to the sample's warp mode.
- **Live.Sample.Sample.warping** _Property_ — `get, set, observe`
  > Access to the sample's warping property.

### Live.Sample.SlicingBeatDivision

  - Enum (11): `sixteenth=sixteenth`, `sixteenth_triplett=sixteenth_triplett`, `eighth=eighth`, `eighth_triplett=eighth_triplett`, `quarter=quarter`, `quarter_triplett=quarter_triplett`, `half=half`, `half_triplett=half_triplett`, `one_bar=one_bar`, `two_bars=two_bars`, `four_bars=four_bars`

### Live.Sample.SlicingStyle

  - Enum (4): `transient=transient`, `beat=beat`, `region=region`, `manual=manual`

### Live.Sample.TransientLoopMode

  - Enum (3): `off=off`, `forward=forward`, `alternate=alternate`

## Live.Scene


### Live.Scene.Scene

> This class represents an series of ClipSlots in Lives Sessionview matrix.

- **Live.Scene.Scene.fire()** _Built-In_
  > fire( (Scene)arg1 [, (bool)force_legato=False [, (bool)can_select_scene_on_launch=True]]) -> None : Fire the scene directly. Will fire all clipslots that this scene owns and select the scene itself. C++ signature :  void fire(TPyHandle<AScene> [,bool=False [,bool=True]])
- **Live.Scene.Scene.fire_as_selected()** _Built-In_
  > fire_as_selected( (Scene)arg1 [, (bool)force_legato=False]) -> None : Fire the selected scene. Will fire all clipslots that this scene owns and select the next scene if necessary. C++ signature :  void fire_as_selected(TPyHandle<AScene> [,bool=False])
- **Live.Scene.Scene.set_fire_button_state()** _Built-In_
  > set_fire_button_state( (Scene)arg1, (bool)arg2) -> None : Set the scene's fire button state directly. Supports all launch modes. C++ signature :  void set_fire_button_state(TPyHandle<AScene>,bool)
- **Live.Scene.Scene.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the scene.
- **Live.Scene.Scene.clip_slots** _Property_RO_ — `get, observe`
  > return a list of clipslots (see class AClipSlot) that this scene covers.
- **Live.Scene.Scene.color** _Property_ — `get, set, observe`
  > Get/set access to the color of the scene (RGB).
- **Live.Scene.Scene.color_index** _Property_ — `get, set, observe`
  > Get/set access to the color index of the scene. Can be None for no color.
- **Live.Scene.Scene.is_empty** _Property_RO_ — `get`
  > Returns True if all clip slots of this scene are empty.
- **Live.Scene.Scene.is_triggered** _Property_RO_ — `get, observe`
  > Const access to the scene's trigger state.
- **Live.Scene.Scene.name** _Property_ — `get, set, observe`
  > Get/Set the name of the scene.
- **Live.Scene.Scene.tempo** _Property_ — `get, set, observe`
  > Get/Set the tempo value of the scene.The song will use the scene's tempo as soon as the scene is fired.Returns -1 if the scene has no tempo property.
- **Live.Scene.Scene.tempo_enabled** _Property_ — `get, set, observe`
  > Get/Set the active state of the scene tempo.When disabled, the scene will use the song's tempo,and the tempo value returned will be -1Returns a bool indicating the state of the scene's tempo
- **Live.Scene.Scene.time_signature_denominator** _Property_ — `get, set, observe`
  > Get/Set the scene's time signature denominator.The song will use the scene's time signature as soon as the scene is fired.Returns -1 if the scene has no time signature property.
- **Live.Scene.Scene.time_signature_enabled** _Property_ — `get, set, observe`
  > Get the active state of the scene time signature.When disabled, the scene will use the song's time signature,and the time signature values returned will be -1Returns a bool indicating the state of the scene's time signature
- **Live.Scene.Scene.time_signature_numerator** _Property_ — `get, set, observe`
  > Get/Set the scene's time signature numerator.The song will use the scene's time signature as soon as the scene is fired.Returns -1 if the scene has no time signature property.

## Live.ShifterDevice


### Live.ShifterDevice.ShifterDevice

> This class represents a Shifter device.

- **Live.ShifterDevice.ShifterDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.ShifterDevice.ShifterDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.ShifterDevice.ShifterDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.ShifterDevice.ShifterDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.ShifterDevice.ShifterDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.ShifterDevice.ShifterDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.ShifterDevice.ShifterDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.ShifterDevice.ShifterDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.ShifterDevice.ShifterDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.ShifterDevice.ShifterDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.ShifterDevice.ShifterDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.ShifterDevice.ShifterDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.ShifterDevice.ShifterDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.ShifterDevice.ShifterDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.ShifterDevice.ShifterDevice.pitch_bend_range** _Property_ — `get, set, observe`
  > Return the pitch bend range for MIDI pitch mode
- **Live.ShifterDevice.ShifterDevice.pitch_mode_index** _Property_ — `get, set, observe`
  > Return the current pitch mode index
- **Live.ShifterDevice.ShifterDevice.pitch_mode_list** _Property_RO_ — `get`
  > Return the current pitch mode list
- **Live.ShifterDevice.ShifterDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.ShifterDevice.ShifterDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.ShifterDevice.ShifterDevice.View

> Representing the view aspects of a device.

- **Live.ShifterDevice.ShifterDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.ShifterDevice.ShifterDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.SimplerDevice

- **Live.SimplerDevice.get_available_voice_numbers()** _Built-In_
  > get_available_voice_numbers() -> IntVector : Get a vector of valid Simpler voice numbers. C++ signature :  std::__1::vector<int, std::__1::allocator<int>> get_available_voice_numbers()

### Live.SimplerDevice.PlaybackMode

  - Enum (3): `classic=classic`, `one_shot=one_shot`, `slicing=slicing`

### Live.SimplerDevice.SimplerDevice

> This class represents a Simpler device.

- **Live.SimplerDevice.SimplerDevice.crop()** _Built-In_
  > crop( (SimplerDevice)self) -> None : Crop the loaded sample to the active area between start- and end marker. Calling this method on an empty simpler raises an error. C++ signature :  void crop(TSimplerDevicePyHandle)
- **Live.SimplerDevice.SimplerDevice.guess_playback_length()** _Built-In_
  > guess_playback_length( (SimplerDevice)self) -> float : Return an estimated beat time for the playback length between start- and end-marker. Calling this method on an empty simpler raises an error. C++ signature :  double guess_playback_length(TSimplerDevicePyHandle)
- **Live.SimplerDevice.SimplerDevice.replace_sample()** _Built-In_
  > replace_sample( (SimplerDevice)self, (object)file_path) -> None : Replaces the loaded samples with the one at the provided path. C++ signature :  void replace_sample(TSimplerDevicePyHandle,TString)
- **Live.SimplerDevice.SimplerDevice.reverse()** _Built-In_
  > reverse( (SimplerDevice)self) -> None : Reverse the loaded sample. Calling this method on an empty simpler raises an error. C++ signature :  void reverse(TSimplerDevicePyHandle)
- **Live.SimplerDevice.SimplerDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.SimplerDevice.SimplerDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.SimplerDevice.SimplerDevice.warp_as()** _Built-In_
  > warp_as( (SimplerDevice)self, (float)beat_time) -> None : Warp the playback region between start- and end-marker as the given length. Calling this method on an empty simpler raises an error. C++ signature :  void warp_as(TSimplerDevicePyHandle,double)
- **Live.SimplerDevice.SimplerDevice.warp_double()** _Built-In_
  > warp_double( (SimplerDevice)self) -> None : Doubles the tempo for region between start- and end-marker. C++ signature :  void warp_double(TSimplerDevicePyHandle)
- **Live.SimplerDevice.SimplerDevice.warp_half()** _Built-In_
  > warp_half( (SimplerDevice)self) -> None : Halves the tempo for region between start- and end-marker. C++ signature :  void warp_half(TSimplerDevicePyHandle)
- **Live.SimplerDevice.SimplerDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.SimplerDevice.SimplerDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.SimplerDevice.SimplerDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.SimplerDevice.SimplerDevice.can_warp_as** _Property_RO_ — `get, observe`
  > Returns true if warp_as is available.
- **Live.SimplerDevice.SimplerDevice.can_warp_double** _Property_RO_ — `get, observe`
  > Returns true if warp_double is available.
- **Live.SimplerDevice.SimplerDevice.can_warp_half** _Property_RO_ — `get, observe`
  > Returns true if warp_half is available.
- **Live.SimplerDevice.SimplerDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.SimplerDevice.SimplerDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.SimplerDevice.SimplerDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.SimplerDevice.SimplerDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.SimplerDevice.SimplerDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.SimplerDevice.SimplerDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.SimplerDevice.SimplerDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.SimplerDevice.SimplerDevice.multi_sample_mode** _Property_RO_ — `get, observe`
  > Returns whether Simpler is in mulit-sample mode.
- **Live.SimplerDevice.SimplerDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.SimplerDevice.SimplerDevice.note_pitch_bend_range** _Property_ — `get, set, observe`
  > Access to the Note Pitch Bend Range in Simpler.
- **Live.SimplerDevice.SimplerDevice.pad_slicing** _Property_ — `get, set, observe`
  > When set to true, slices can be added in slicing mode by playing notes .that are not assigned to slices, yet.
- **Live.SimplerDevice.SimplerDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.SimplerDevice.SimplerDevice.pitch_bend_range** _Property_ — `get, set, observe`
  > Access to the Pitch Bend Range in Simpler.
- **Live.SimplerDevice.SimplerDevice.playback_mode** _Property_ — `get, set, observe`
  > Access to Simpler's playback mode.
- **Live.SimplerDevice.SimplerDevice.playing_position** _Property_RO_ — `get, observe`
  > Constant access to the current playing position in the sample.The returned value is the normalized position between sample start and end.
- **Live.SimplerDevice.SimplerDevice.playing_position_enabled** _Property_RO_ — `get, observe`
  > Returns whether Simpler is showing the playing position.The returned value is True while the sample is played back
- **Live.SimplerDevice.SimplerDevice.retrigger** _Property_ — `get, set, observe`
  > Access to Simpler's retrigger mode.
- **Live.SimplerDevice.SimplerDevice.sample** _Property_RO_ — `get, observe`
  > Get the loaded Sample.
- **Live.SimplerDevice.SimplerDevice.slicing_playback_mode** _Property_ — `get, set, observe`
  > Access to Simpler's slicing playback mode.
- **Live.SimplerDevice.SimplerDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.SimplerDevice.SimplerDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.
- **Live.SimplerDevice.SimplerDevice.voices** _Property_ — `get, set, observe`
  > Access to the number of voices in Simpler.

#### Live.SimplerDevice.SimplerDevice.View

> Representing the view aspects of a simpler device.

- **Live.SimplerDevice.SimplerDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.SimplerDevice.SimplerDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.
- **Live.SimplerDevice.SimplerDevice.View.sample_end** _Property_RO_ — `get, observe`
  > Access to the modulated samples end position in samples. Returns -1 in case there is no sample loaded.
- **Live.SimplerDevice.SimplerDevice.View.sample_env_fade_in** _Property_RO_ — `get, observe`
  > Access to the envelope fade-in time in samples. Returned value is only in use when Simpler is in one-shot mode. Returns -1 in case there is no sample loaded.
- **Live.SimplerDevice.SimplerDevice.View.sample_env_fade_out** _Property_RO_ — `get, observe`
  > Access to the envelope fade-out time in samples. Returned value is only in use when Simpler is in one-shot mode. Returns -1 in case there is no sample loaded.
- **Live.SimplerDevice.SimplerDevice.View.sample_loop_end** _Property_RO_ — `get, observe`
  > Access to the modulated samples loop end position in samples. Returns -1 in case there is no sample loaded.
- **Live.SimplerDevice.SimplerDevice.View.sample_loop_fade** _Property_RO_ — `get, observe`
  > Access to the modulated samples loop fade position in samples. Returns -1 in case there is no sample loaded.
- **Live.SimplerDevice.SimplerDevice.View.sample_loop_start** _Property_RO_ — `get, observe`
  > Access to the modulated samples loop start position in samples. Returns -1 in case there is no sample loaded.
- **Live.SimplerDevice.SimplerDevice.View.sample_start** _Property_RO_ — `get, observe`
  > Access to the modulated samples start position in samples. Returns -1 in case there is no sample loaded.
- **Live.SimplerDevice.SimplerDevice.View.selected_slice** _Property_ — `get, set, observe`
  > Access to the selected slice.

### Live.SimplerDevice.SlicingPlaybackMode

  - Enum (3): `mono=mono`, `poly=poly`, `thru=thru`

## Live.Song

- **Live.Song.get_all_scales_ordered()** _Built-In_
  > get_all_scales_ordered() -> tuple : Get an ordered tuple of tuples of all available scale names to intervals. C++ signature :  boost::python::tuple get_all_scales_ordered()

### Live.Song.BeatTime

> Represents a Time, splitted into Bars, Beats, SubDivision and Ticks.

- **Live.Song.BeatTime.bars** _Property_ — `get, set`
- **Live.Song.BeatTime.beats** _Property_ — `get, set`
- **Live.Song.BeatTime.sub_division** _Property_ — `get, set`
- **Live.Song.BeatTime.ticks** _Property_ — `get, set`

### Live.Song.CaptureDestination

> The destination for MIDI capture.

  - Enum (3): `auto=auto`, `session=session`, `arrangement=arrangement`

### Live.Song.CaptureMode

> The capture mode that is used for capture and insert scene.

  - Enum (2): `all=all`, `all_except_selected=all_except_selected`

### Live.Song.CuePoint

> Represents a 'Marker' in the arrangement.

- **Live.Song.CuePoint.jump()** _Built-In_
  > jump( (CuePoint)arg1) -> None : When the Song is playing, set the playing-position quantized to this Cuepoint's time. When not playing, simply move the start playing position. C++ signature :  void jump(TPyHandle<ACuePoint>)
- **Live.Song.CuePoint.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the cue point.
- **Live.Song.CuePoint.name** _Property_ — `get, set, observe`
  > Get/Set/Listen to the name of this CuePoint, as visible in the arranger.
- **Live.Song.CuePoint.time** _Property_RO_ — `get, observe`
  > Get/Listen to the CuePoint's time in beats.

### Live.Song.Quantization

  - Enum (14): `q_no_q=q_no_q`, `q_8_bars=q_8_bars`, `q_4_bars=q_4_bars`, `q_2_bars=q_2_bars`, `q_bar=q_bar`, `q_half=q_half`, `q_half_triplet=q_half_triplet`, `q_quarter=q_quarter`, `q_quarter_triplet=q_quarter_triplet`, `q_eight=q_eight`, `q_eight_triplet=q_eight_triplet`, `q_sixtenth=q_sixtenth`, `q_sixtenth_triplet=q_sixtenth_triplet`, `q_thirtytwoth=q_thirtytwoth`

### Live.Song.RecordingQuantization

  - Enum (9): `rec_q_no_q=rec_q_no_q`, `rec_q_quarter=rec_q_quarter`, `rec_q_eight=rec_q_eight`, `rec_q_eight_triplet=rec_q_eight_triplet`, `rec_q_eight_eight_triplet=rec_q_eight_eight_triplet`, `rec_q_sixtenth=rec_q_sixtenth`, `rec_q_sixtenth_triplet=rec_q_sixtenth_triplet`, `rec_q_sixtenth_sixtenth_triplet=rec_q_sixtenth_sixtenth_triplet`, `rec_q_thirtysecond=rec_q_thirtysecond`

### Live.Song.SessionRecordStatus

  - Enum (3): `off=off`, `on=on`, `transition=transition`

### Live.Song.SmptTime

> Represents a Time, split into Hours, Minutes, Seconds and Frames.The frame type must be specified when calling a function that returnsa SmptTime.

- **Live.Song.SmptTime.frames** _Property_ — `get, set`
- **Live.Song.SmptTime.hours** _Property_ — `get, set`
- **Live.Song.SmptTime.minutes** _Property_ — `get, set`
- **Live.Song.SmptTime.seconds** _Property_ — `get, set`

### Live.Song.Song

> This class represents a Live set.

- **Live.Song.Song.begin_undo_step()** _Built-In_
  > begin_undo_step( (Song)arg1) -> None : C++ signature :  void begin_undo_step(TPyHandle<ASong>)
- **Live.Song.Song.capture_and_insert_scene()** _Built-In_
  > capture_and_insert_scene( (Song)arg1 [, (int)CaptureMode=Song.CaptureMode.all]) -> None : Capture currently playing clips and insert them as a new scene after the selected scene. Raises a runtime error if creating a new scene would exceed the limitations. C++ signature :  void capture_and_insert_scene(TPyHandle<ASong> [,int=Song.CaptureMode.all])
- **Live.Song.Song.capture_midi()** _Built-In_
  > capture_midi( (Song)arg1 [, (int)Destination=Song.CaptureDestination.auto]) -> None : Capture recently played MIDI material from audible tracks. If no Destination is given or Destination is set to CaptureDestination.auto, the captured material is inserted into the Session or Arrangement depending on which is visible. If Destination is set to CaptureDestination.session or CaptureDestination.arrangement, inserts the material into Session or Arrangement, respectively. Raises a limitation error when capturing into the Session and a new scene would have to be created but can't because it would exceed the limitations. C++ signature :  void capture_midi(TPyHandle<ASong> [,int=Song.CaptureDestination.auto])
- **Live.Song.Song.continue_playing()** _Built-In_
  > continue_playing( (Song)arg1) -> None : Continue playing the song from the current position C++ signature :  void continue_playing(TPyHandle<ASong>)
- **Live.Song.Song.create_audio_track()** _Built-In_
  > create_audio_track( (Song)arg1 [, (object)Index=None]) -> Track : Create a new audio track at the optional given index and return it.If the index is -1, the new track is added at the end. It will create a default audio track if possible. If the index is invalid or the new track would exceed the limitations, a limitation error is raised.If the index is missing, the track is created after the last selected item C++ signature :  TWeakPtr<TTrackPyHandle> create_audio_track(TPyHandle<ASong> [,boost::python::api::object=None])
- **Live.Song.Song.create_midi_track()** _Built-In_
  > create_midi_track( (Song)arg1 [, (object)Index=None]) -> Track : Create a new midi track at the optional given index and return it.If the index is -1,  the new track is added at the end.It will create a default midi track if possible. If the index is invalid or the new track would exceed the limitations, a limitation error is raised.If the index is missing, the track is created after the last selected item C++ signature :  TWeakPtr<TTrackPyHandle> create_midi_track(TPyHandle<ASong> [,boost::python::api::object=None])
- **Live.Song.Song.create_return_track()** _Built-In_
  > create_return_track( (Song)arg1) -> Track : Create a new return track at the end and return it. If the new track would exceed  the limitations, a limitation error is raised.  If the maximum number of return tracks is exceeded, a RuntimeError is raised. C++ signature :  TWeakPtr<TTrackPyHandle> create_return_track(TPyHandle<ASong>)
- **Live.Song.Song.create_scene()** _Built-In_
  > create_scene( (Song)arg1, (int)arg2) -> Scene : Create a new scene at the given index. If the index is -1, the new scene is added at the end. If the index is invalid or the new scene would exceed the limitations, a limitation error is raised. C++ signature :  TWeakPtr<TPyHandle<AScene>> create_scene(TPyHandle<ASong>,int)
- **Live.Song.Song.delete_return_track()** _Built-In_
  > delete_return_track( (Song)arg1, (int)arg2) -> None : Delete the return track with the given index. If no track with this index exists, an exception will be raised. C++ signature :  void delete_return_track(TPyHandle<ASong>,int)
- **Live.Song.Song.delete_scene()** _Built-In_
  > delete_scene( (Song)arg1, (int)arg2) -> None : Delete the scene with the given index. If no scene with this index exists, an exception will be raised. C++ signature :  void delete_scene(TPyHandle<ASong>,int)
- **Live.Song.Song.delete_track()** _Built-In_
  > delete_track( (Song)arg1, (int)arg2) -> None : Delete the track with the given index. If no track with this index exists, an exception will be raised. C++ signature :  void delete_track(TPyHandle<ASong>,int)
- **Live.Song.Song.duplicate_scene()** _Built-In_
  > duplicate_scene( (Song)arg1, (int)arg2) -> None : Duplicates a scene and selects the new one. Raises a limitation error if creating a new scene would exceed the limitations. C++ signature :  void duplicate_scene(TPyHandle<ASong>,int)
- **Live.Song.Song.duplicate_track()** _Built-In_
  > duplicate_track( (Song)arg1, (int)arg2) -> None : Duplicates a track and selects the new one. If the track is inside a folded group track, the group track is unfolded. Raises a limitation error if creating a new track would exceed the limitations. C++ signature :  void duplicate_track(TPyHandle<ASong>,int)
- **Live.Song.Song.end_undo_step()** _Built-In_
  > end_undo_step( (Song)arg1) -> None : C++ signature :  void end_undo_step(TPyHandle<ASong>)
- **Live.Song.Song.find_device_position()** _Built-In_
  > find_device_position( (Song)arg1, (Device)device, (LomObject)target, (int)target_position) -> int : Returns the closest possible position to the given target, where the device can be inserted. If inserting is not possible at all (i.e. if the device type is wrong), -1 is returned. C++ signature :  int find_device_position(TPyHandle<ASong>,TPyHandle<ADevice>,TPyHandleBase,int)
- **Live.Song.Song.force_link_beat_time()** _Built-In_
  > force_link_beat_time( (Song)arg1) -> None : Force the Link timeline to jump to Lives current beat time. Danger: This can cause beat time discontinuities in other connected apps. C++ signature :  void force_link_beat_time(TPyHandle<ASong>)
- **Live.Song.Song.get_beats_loop_length()** _Built-In_
  > get_beats_loop_length( (Song)arg1) -> BeatTime : Get const access to the songs loop length, using a BeatTime class with the current global set signature. C++ signature :  NSongApi::TBeatTime get_beats_loop_length(TPyHandle<ASong>)
- **Live.Song.Song.get_beats_loop_start()** _Built-In_
  > get_beats_loop_start( (Song)arg1) -> BeatTime : Get const access to the songs loop start, using a BeatTime class with the current global set signature. C++ signature :  NSongApi::TBeatTime get_beats_loop_start(TPyHandle<ASong>)
- **Live.Song.Song.get_current_beats_song_time()** _Built-In_
  > get_current_beats_song_time( (Song)arg1) -> BeatTime : Get const access to the songs current playing position, using a BeatTime class with the current global set signature. C++ signature :  NSongApi::TBeatTime get_current_beats_song_time(TPyHandle<ASong>)
- **Live.Song.Song.get_current_smpte_song_time()** _Built-In_
  > get_current_smpte_song_time( (Song)arg1, (int)arg2) -> SmptTime : Get const access to the songs current playing position, by specifying the SMPTE format in which you would like to receive the time. C++ signature :  NSongApi::TSmptTime get_current_smpte_song_time(TPyHandle<ASong>,int)
- **Live.Song.Song.get_data()** _Built-In_
  > get_data( (Song)arg1, (object)key, (object)default_value) -> object : Get data for the given key, that was previously stored using set_data. C++ signature :  boost::python::api::object get_data(TPyHandle<ASong>,TString,boost::python::api::object)
- **Live.Song.Song.is_cue_point_selected()** _Built-In_
  > is_cue_point_selected( (Song)arg1) -> bool : Return true if the global playing pos is currently on a cue point. C++ signature :  bool is_cue_point_selected(TPyHandle<ASong>)
- **Live.Song.Song.jump_by()** _Built-In_
  > jump_by( (Song)arg1, (float)arg2) -> None : Set a new playing pos, relative to the current one. C++ signature :  void jump_by(TPyHandle<ASong>,double)
- **Live.Song.Song.jump_to_next_cue()** _Built-In_
  > jump_to_next_cue( (Song)arg1) -> None : Jump to the next cue (marker) if possible. C++ signature :  void jump_to_next_cue(TPyHandle<ASong>)
- **Live.Song.Song.jump_to_prev_cue()** _Built-In_
  > jump_to_prev_cue( (Song)arg1) -> None : Jump to the prior cue (marker) if possible. C++ signature :  void jump_to_prev_cue(TPyHandle<ASong>)
- **Live.Song.Song.move_device()** _Built-In_
  > move_device( (Song)arg1, (Device)device, (LomObject)target, (int)target_position) -> int : Move a device into the target at the given position, where 0 moves it before the first device and len(devices) moves it to the end of the device chain.If the device cannot be moved to this position, the nearest possible position is chosen. If the device type is not valid, a runtime error is raised.Returns the index, where the device was moved to. C++ signature :  int move_device(TPyHandle<ASong>,TPyHandle<ADevice>,TPyHandleBase,int)
- **Live.Song.Song.play_selection()** _Built-In_
  > play_selection( (Song)arg1) -> None : Start playing the current set selection, or do nothing if no selection is set. C++ signature :  void play_selection(TPyHandle<ASong>)
- **Live.Song.Song.re_enable_automation()** _Built-In_
  > re_enable_automation( (Song)arg1) -> None : Discards overrides of automated parameters. C++ signature :  void re_enable_automation(TPyHandle<ASong>)
- **Live.Song.Song.redo()** _Built-In_
  > redo( (Song)arg1) -> str : Redo the last action that was undone. C++ signature :  TString redo(TPyHandle<ASong>)
- **Live.Song.Song.scrub_by()** _Built-In_
  > scrub_by( (Song)arg1, (float)arg2) -> None : Same as jump_by, but does not stop playback. C++ signature :  void scrub_by(TPyHandle<ASong>,double)
- **Live.Song.Song.set_data()** _Built-In_
  > set_data( (Song)arg1, (object)key, (object)value) -> None : Store data for the given key in this object. The data is persistent and will be restored when loading the Live Set. C++ signature :  void set_data(TPyHandle<ASong>,TString,boost::python::api::object)
- **Live.Song.Song.set_or_delete_cue()** _Built-In_
  > set_or_delete_cue( (Song)arg1) -> None : When a cue is selected, it gets deleted. If no cue is selected, a new cue is created at the current global songtime. C++ signature :  void set_or_delete_cue(TPyHandle<ASong>)
- **Live.Song.Song.start_playing()** _Built-In_
  > start_playing( (Song)arg1) -> None : Start playing from the startmarker C++ signature :  void start_playing(TPyHandle<ASong>)
- **Live.Song.Song.stop_all_clips()** _Built-In_
  > stop_all_clips( (Song)arg1 [, (bool)Quantized=True]) -> None : Stop all playing Clips (if any) but continue playing the Song. C++ signature :  void stop_all_clips(TPyHandle<ASong> [,bool=True])
- **Live.Song.Song.stop_playing()** _Built-In_
  > stop_playing( (Song)arg1) -> None : Stop playing the Song. C++ signature :  void stop_playing(TPyHandle<ASong>)
- **Live.Song.Song.tap_tempo()** _Built-In_
  > tap_tempo( (Song)arg1) -> None : Trigger the tap tempo function. C++ signature :  void tap_tempo(TPyHandle<ASong>)
- **Live.Song.Song.trigger_session_record()** _Built-In_
  > trigger_session_record( (Song)self [, (float)record_length=1.7976931348623157e+308]) -> None : Triggers a new session recording. C++ signature :  void trigger_session_record(TPyHandle<ASong> [,double=1.7976931348623157e+308])
- **Live.Song.Song.undo()** _Built-In_
  > undo( (Song)arg1) -> str : Undo the last action that was made. C++ signature :  TString undo(TPyHandle<ASong>)
- **Live.Song.Song.appointed_device** _Property_ — `get, set, observe`
  > Read, write, and listen access to the appointed Device
- **Live.Song.Song.arrangement_overdub** _Property_ — `get, set, observe`
  > Get/Set the global arrangement overdub state.
- **Live.Song.Song.back_to_arranger** _Property_ — `get, set, observe`
  > Get/Set if triggering a Clip in the Session, disabled the playback ofClips in the Arranger.
- **Live.Song.Song.can_capture_midi** _Property_RO_ — `get, observe`
  > Get whether there currently is material to be captured on any tracks.
- **Live.Song.Song.can_jump_to_next_cue** _Property_RO_ — `get, observe`
  > Returns true when there is a cue marker right to the playing pos thatwe could jump to.
- **Live.Song.Song.can_jump_to_prev_cue** _Property_RO_ — `get, observe`
  > Returns true when there is a cue marker left to the playing pos thatwe could jump to.
- **Live.Song.Song.can_redo** _Property_RO_ — `get`
  > Returns true if there is an undone action that we can redo.
- **Live.Song.Song.can_undo** _Property_RO_ — `get`
  > Returns true if there is an action that we can restore.
- **Live.Song.Song.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the song.
- **Live.Song.Song.clip_trigger_quantization** _Property_ — `get, set, observe`
  > Get/Set access to the quantization settings that are used to fireClips in the Session.
- **Live.Song.Song.count_in_duration** _Property_RO_ — `get, observe`
  > Get the count in duration. Returns an index, mapped as follows: 0 - None, 1 - 1 Bar, 2 - 2 Bars, 3 - 4 Bars.
- **Live.Song.Song.cue_points** _Property_RO_ — `get, observe`
  > Const access to a list of all cue points of the Live Song.
- **Live.Song.Song.current_song_time** _Property_ — `get, set, observe`
  > Get/Set access to the songs current playing position in beats.
- **Live.Song.Song.exclusive_arm** _Property_RO_ — `get, observe`
  > Get if Tracks should be armed exclusively by default.
- **Live.Song.Song.exclusive_solo** _Property_RO_ — `get`
  > Get if Tracks should be soloed exclusively by default.
- **Live.Song.Song.file_path** _Property_RO_ — `get`
  > Get the current Live Set's path on disk.
- **Live.Song.Song.groove_amount** _Property_ — `get, set, observe`
  > Get/Set the global groove amount, that adjust all setup groovesin all clips.
- **Live.Song.Song.groove_pool** _Property_RO_ — `get`
  > Get the groove pool.
- **Live.Song.Song.is_ableton_link_enabled** _Property_ — `get, set, observe`
  > Enable/disable Ableton Link.
- **Live.Song.Song.is_ableton_link_start_stop_sync_enabled** _Property_ — `get, set, observe`
  > Enable/disable Ableton Link Start Stop Sync.
- **Live.Song.Song.is_counting_in** _Property_RO_ — `get, observe`
  > Get whether currently counting in.
- **Live.Song.Song.is_playing** _Property_ — `get, set, observe`
  > Returns true if the Song is currently playing.
- **Live.Song.Song.last_event_time** _Property_RO_ — `get`
  > Return the time of the last set event in the song. In contrary tosong_length, this will not add some extra beats that are mostly neededfor Display purposes in the Arrangerview.
- **Live.Song.Song.loop** _Property_ — `get, set, observe`
  > Get/Set the looping flag that en/disables the usage of the globalloop markers in the song.
- **Live.Song.Song.loop_length** _Property_ — `get, set, observe`
  > Get/Set the length of the global loop marker position in beats.
- **Live.Song.Song.loop_start** _Property_ — `get, set, observe`
  > Get/Set the start of the global loop marker position in beats.
- **Live.Song.Song.master_track** _Property_RO_ — `get`
  > Access to the Main Track (always available)
- **Live.Song.Song.metronome** _Property_ — `get, set, observe`
  > Get/Set if the metronom is audible.
- **Live.Song.Song.midi_recording_quantization** _Property_ — `get, set, observe`
  > Get/Set access to the settings that are used to quantizeMIDI recordings.
- **Live.Song.Song.name** _Property_RO_ — `get`
  > Get the current Live Set's name.
- **Live.Song.Song.nudge_down** _Property_ — `get, set, observe`
  > Get/Set the status of the nudge down button.
- **Live.Song.Song.nudge_up** _Property_ — `get, set, observe`
  > Get/Set the status of the nudge up button.
- **Live.Song.Song.overdub** _Property_ — `get, set, observe`
  > Legacy hook for Live 8 overdub state. Now hooks tosession record, but never starts playback.
- **Live.Song.Song.punch_in** _Property_ — `get, set, observe`
  > Get/Set the flag that will enable recording as soon as the Song playsand hits the global loop start region.
- **Live.Song.Song.punch_out** _Property_ — `get, set, observe`
  > Get/Set the flag that will disable recording as soon as the Song playsand hits the global loop end region.
- **Live.Song.Song.re_enable_automation_enabled** _Property_RO_ — `get, observe`
  > Returns true if some automated parameter has been overriden
- **Live.Song.Song.record_mode** _Property_ — `get, set, observe`
  > Get/Set the state of the global recording flag.
- **Live.Song.Song.return_tracks** _Property_RO_ — `get, observe`
  > Const access to the list of available Return Tracks.
- **Live.Song.Song.root_note** _Property_ — `get, set, observe`
  > Set and access the root (i.e. key) of the song. The root can be a number between 0 and 11, with 0 corresponding to C and 11 corresponding to B.
- **Live.Song.Song.scale_intervals** _Property_RO_ — `get, observe`
  > Reports the current scale's intervals as a list of integers, starting with the root and representing the number of halfsteps (e.g. Major -> 0, 2, 4, 5, 7, 9, 11)
- **Live.Song.Song.scale_mode** _Property_ — `get, set, observe`
  > Access to the Scale Mode setting in Live. When on, key tracks that belong to the currently selected scale are highlighted in Live's MIDI Note Editor, and pitch-based parameters in MIDI Tools and Devices can be edited in scale degrees rather than semitones.
- **Live.Song.Song.scale_name** _Property_ — `get, set, observe`
  > Set and access the currently selected scale by name. The default scale names that can be saved with a set and recalled are'Major', 'Minor', 'Dorian', 'Mixolydian' ,'Lydian' ,'Phrygian' ,'Locrian', 'Whole Tone', 'Half-whole Dim.', 'Whole-half Dim.', 'Minor Blues', 'Minor Pentatonic', 'Major Pentatonic', 'Harmonic Minor', 'Harmonic Major', 'Dorian #4', 'Phrygian Dominant', 'Melodic Minor', 'Lydian Augmented', 'Lydian Dominant', 'Super Locrian', 'Bhairav', 'Hungarian Minor', '8-Tone Spanish', 'Hirajoshi', 'In-Sen', 'Iwato', 'Kumoi', 'Pelog Selisir', 'Pelog Tembung', 'Messiaen 3', 'Messiaen 4', 'Messiaen 5', 'Messiaen 6', 'Messiaen 7'
- **Live.Song.Song.scenes** _Property_RO_ — `get, observe`
  > Const access to a list of all Scenes in the Live Song.
- **Live.Song.Song.select_on_launch** _Property_RO_ — `get`
  > Get if Scenes and Clips should be selected when fired.
- **Live.Song.Song.session_automation_record** _Property_ — `get, set, observe`
  > Returns true if automation recording is enabled.
- **Live.Song.Song.session_record** _Property_ — `get, set, observe`
  > Get/Set the session record state.
- **Live.Song.Song.session_record_status** _Property_RO_ — `get, observe`
  > Get the session slot-recording state.
- **Live.Song.Song.signature_denominator** _Property_ — `get, set, observe`
  > Get/Set access to the global signature denominator of the Song.
- **Live.Song.Song.signature_numerator** _Property_ — `get, set, observe`
  > Get/Set access to the global signature numerator of the Song.
- **Live.Song.Song.song_length** _Property_RO_ — `get, observe`
  > Return the time of the last set event in the song, plus som extra beatsthat are usually added for better navigation in the arrangerview.
- **Live.Song.Song.start_time** _Property_ — `get, set, observe`
  > Get/Set access to the songs current start time in beats. The set timemay be overridden by the current loop/locator start time.
- **Live.Song.Song.swing_amount** _Property_ — `get, set, observe`
  > Get/Set access to the amount of swing that is applied when adding or quantizing notes to MIDI clips
- **Live.Song.Song.tempo** _Property_ — `get, set, observe`
  > Get/Set the global project tempo.
- **Live.Song.Song.tempo_follower_enabled** _Property_ — `get, set, observe`
  > Get/Set whether the Tempo Follower is controlling the tempo. The Tempo Follower Toggle must be made visible in the preferences for this property to be effective.
- **Live.Song.Song.tracks** _Property_RO_ — `get, observe`
  > Const access to a list of all Player Tracks in the Live Song, excludingthe return and Main Track (see also Song.send_tracks and Song.master_track).At least one MIDI or Audio Track is always available.
- **Live.Song.Song.tuning_system** _Property_RO_ — `get, observe`
  > Access the currently active tuning system.
- **Live.Song.Song.view** _Property_RO_ — `get`
  > Representing the view aspects of a Live document: The Session and Arrangerview.
- **Live.Song.Song.visible_tracks** _Property_RO_ — `get, observe`
  > Const access to a list of all visible Player Tracks in the Live Song, excludingthe return and Main Track (see also Song.send_tracks and Song.master_track).At least one MIDI or Audio Track is always available.

#### Live.Song.Song.View

> Representing the view aspects of a Live document: The Session and Arrangerview.

- **Live.Song.Song.View.select_device()** _Built-In_
  > select_device( (View)arg1, (Device)arg2 [, (bool)ShouldAppointDevice=True]) -> None : Select the given device. C++ signature :  void select_device(TPyViewData<ASong>,TPyHandle<ADevice> [,bool=True])
- **Live.Song.Song.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the song view.
- **Live.Song.Song.View.detail_clip** _Property_ — `get, set, observe`
  > Get/Set the Clip that is currently visible in Lives Detailview.
- **Live.Song.Song.View.draw_mode** _Property_ — `get, set, observe`
  > Get/Set if the Envelope/Note draw mode is enabled.
- **Live.Song.Song.View.follow_song** _Property_ — `get, set, observe`
  > Get/Set if the Arrangerview should scroll to show the playmarker.
- **Live.Song.Song.View.highlighted_clip_slot** _Property_ — `get, set`
  > Get/Set the clip slot, defined via the selected track and scene in the Session.Will be None for Main- and Sendtracks.
- **Live.Song.Song.View.mod_mapping_device** _Property_ — `get, set, observe`
  > The device that is waiting for a parameter (via mod_mapping_parameter) to modulate, or None if no device is waiting.
- **Live.Song.Song.View.mod_mapping_parameter** _Property_RO_ — `get, observe`
  > Get the device parameter that's current selected to be mapped.
- **Live.Song.Song.View.selected_chain** _Property_ — `get, set, observe`
  > Get the highlighted chain if available.
- **Live.Song.Song.View.selected_parameter** _Property_RO_ — `get, observe`
  > Get the currently selected device parameter.
- **Live.Song.Song.View.selected_scene** _Property_ — `get, set, observe`
  > Get/Set the current selected scene in Lives Sessionview.
- **Live.Song.Song.View.selected_track** _Property_ — `get, set, observe`
  > Get/Set the current selected Track in Lives Session or Arrangerview.

### Live.Song.TimeFormat

  - Enum (6): `ms_time=ms_time`, `smpte_24=smpte_24`, `smpte_25=smpte_25`, `smpte_30=smpte_30`, `smpte_30_drop=smpte_30_drop`, `smpte_29=smpte_29`

## Live.SpectralResonatorDevice


### Live.SpectralResonatorDevice.SpectralResonatorDevice

> This class represents a Spectral Resonator device.

- **Live.SpectralResonatorDevice.SpectralResonatorDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.frequency_dial_mode** _Property_ — `get, set, observe`
  > Return the current frequency dial mode index
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.frequency_dial_mode_list** _Property_RO_ — `get, observe`
  > Return the current frequency dial mode list
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.midi_gate** _Property_ — `get, set, observe`
  > Return the current midi gate index
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.midi_gate_list** _Property_RO_ — `get, observe`
  > Return the current midi gate list
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.mod_mode** _Property_ — `get, set, observe`
  > Return the current mod mode index
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.mod_mode_list** _Property_RO_ — `get, observe`
  > Return the current mod mode list
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.mono_poly** _Property_ — `get, set, observe`
  > Return the current mono poly mode index
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.mono_poly_list** _Property_RO_ — `get, observe`
  > Return the current mono poly mode list
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.pitch_bend_range** _Property_ — `get, set, observe`
  > Return the current pitch bend range
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.pitch_mode** _Property_ — `get, set, observe`
  > Return the current pitch mode index
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.pitch_mode_list** _Property_RO_ — `get, observe`
  > Return the current pitch mode list
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.polyphony** _Property_ — `get, set, observe`
  > Return the current polyphony
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.

#### Live.SpectralResonatorDevice.SpectralResonatorDevice.View

> Representing the view aspects of a device.

- **Live.SpectralResonatorDevice.SpectralResonatorDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.SpectralResonatorDevice.SpectralResonatorDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.

## Live.TakeLane


### Live.TakeLane.TakeLane

> This class represents a take lane in Live.

- **Live.TakeLane.TakeLane.create_audio_clip()** _Built-In_
  > create_audio_clip( (TakeLane)arg1, (object)arg2, (float)arg3) -> Clip : Creates an audio clip referencing the file at the given path and inserts it into the arrangement at the specified time. Throws an error when called on a non-audio or a frozen track, when the specified time is outside the [0., 1576800.] range, when the track is currently being recorded into, or when the path doesn't point to a valid audio file. C++ signature :  TWeakPtr<TPyHandle<AClip>> create_audio_clip(TPyHandle<ATakeLane>,TString,double)
- **Live.TakeLane.TakeLane.create_midi_clip()** _Built-In_
  > create_midi_clip( (TakeLane)arg1, (float)arg2, (float)arg3) -> Clip : Creates an empty MIDI clip and inserts it into the arrangement at the specified time. Throws an error when called on a non-MIDI track or a frozen track, when the specified time is outside the [0., 1576800.] range, or when the track is currently being recorded into. C++ signature :  TWeakPtr<TPyHandle<AClip>> create_midi_clip(TPyHandle<ATakeLane>,double,double)
- **Live.TakeLane.TakeLane.arrangement_clips** _Property_RO_ — `get, observe`
  > Read-only access to the arrangement clips in the take lane.
- **Live.TakeLane.TakeLane.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the take lane.
- **Live.TakeLane.TakeLane.name** _Property_ — `get, set, observe`
  > Read/write access to the name of the TakeLane, as visible in the take lane header.

## Live.Track


### Live.Track.DeviceContainer

> This class is a common super class of Track and Chain


### Live.Track.DeviceInsertMode

  - Enum (4): `default=default`, `selected_left=selected_left`, `selected_right=selected_right`, `count=count`

### Live.Track.RoutingChannel

> This class represents a routing channel.

- **Live.Track.RoutingChannel.display_name** _Property_RO_ — `get`
  > Display name of routing channel.
- **Live.Track.RoutingChannel.layout** _Property_RO_ — `get`
  > The routing channel's Layout, e.g., mono or stereo.

### Live.Track.RoutingChannelLayout

  - Enum (3): `midi=midi`, `mono=mono`, `stereo=stereo`

### Live.Track.RoutingChannelVector

> A container for returning routing channels from Live.

- **Live.Track.RoutingChannelVector.append()** _Built-In_
  > append( (RoutingChannelVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<NRoutingApi::TRoutingChannel, std::__1::allocator<NRoutingApi::TRoutingChannel>> {lvalue},boost::python::api::object)
- **Live.Track.RoutingChannelVector.extend()** _Built-In_
  > extend( (RoutingChannelVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<NRoutingApi::TRoutingChannel, std::__1::allocator<NRoutingApi::TRoutingChannel>> {lvalue},boost::python::api::object)

### Live.Track.RoutingType

> This class represents a routing type.

- **Live.Track.RoutingType.attached_object** _Property_RO_ — `get`
  > Live object associated with the routing type.
- **Live.Track.RoutingType.category** _Property_RO_ — `get`
  > Category of the routing type.
- **Live.Track.RoutingType.display_name** _Property_RO_ — `get`
  > Display name of routing type.

### Live.Track.RoutingTypeCategory

  - Enum (8): `external=external`, `rewire=rewire`, `resampling=resampling`, `master=master`, `track=track`, `parent_group_track=parent_group_track`, `none=none`, `invalid=invalid`

### Live.Track.RoutingTypeVector

> A container for returning routing types from Live.

- **Live.Track.RoutingTypeVector.append()** _Built-In_
  > append( (RoutingTypeVector)arg1, (object)arg2) -> None : C++ signature :  void append(std::__1::vector<NRoutingApi::TRoutingType, std::__1::allocator<NRoutingApi::TRoutingType>> {lvalue},boost::python::api::object)
- **Live.Track.RoutingTypeVector.extend()** _Built-In_
  > extend( (RoutingTypeVector)arg1, (object)arg2) -> None : C++ signature :  void extend(std::__1::vector<NRoutingApi::TRoutingType, std::__1::allocator<NRoutingApi::TRoutingType>> {lvalue},boost::python::api::object)

### Live.Track.Track

> This class represents a track in Live. It can be either an Audio track, a MIDI Track, a Return Track or the Main track. The Main Track and at least one Audio or MIDI track will be always present.Return Tracks are optional.

- **Live.Track.Track.create_audio_clip()** _Built-In_
  > create_audio_clip( (Track)arg1, (object)arg2, (float)arg3) -> Clip : Creates an audio clip referencing the file at the given path and inserts it into the arrangement at the specified time. Throws an error when called on a non-audio or a frozen track, when the specified time is outside the [0., 1576800.] range, when the track is currently being recorded into, or when the path doesn't point to a valid audio file. C++ signature :  TWeakPtr<TPyHandle<AClip>> create_audio_clip(TTrackPyHandle,TString,double)
- **Live.Track.Track.create_midi_clip()** _Built-In_
  > create_midi_clip( (Track)arg1, (float)arg2, (float)arg3) -> Clip : Creates an empty MIDI clip and inserts it into the arrangement at the specified time. Throws an error when called on a non-MIDI track or a frozen track, when the specified time is outside the [0., 1576800.] range, or when the track is currently being recorded into. C++ signature :  TWeakPtr<TPyHandle<AClip>> create_midi_clip(TTrackPyHandle,double,double)
- **Live.Track.Track.create_take_lane()** _Built-In_
  > create_take_lane( (Track)arg1) -> LomObject : Create a new TakeLane for this track. C++ signature :  TWeakPtr<TPyHandleBase> create_take_lane(TTrackPyHandle)
- **Live.Track.Track.delete_clip()** _Built-In_
  > delete_clip( (Track)arg1, (Clip)arg2) -> None : Delete the given clip. Raises a runtime error when the clip belongs to another track. C++ signature :  void delete_clip(TTrackPyHandle,TPyHandle<AClip>)
- **Live.Track.Track.delete_device()** _Built-In_
  > delete_device( (Track)arg1, (int)arg2) -> None : Delete a device identified by the index in the 'devices' list. C++ signature :  void delete_device(TTrackPyHandle,int)
- **Live.Track.Track.duplicate_clip_slot()** _Built-In_
  > duplicate_clip_slot( (Track)arg1, (int)arg2) -> int : Duplicate a clip and put it into the next free slot and return the index of the destination slot. A new scene is created if no free slot is available. If creating the new scene would exceed the limitations, a runtime error is raised. C++ signature :  int duplicate_clip_slot(TTrackPyHandle,int)
- **Live.Track.Track.duplicate_clip_to_arrangement()** _Built-In_
  > duplicate_clip_to_arrangement( (Track)self, (Clip)clip, (float)destination_time) -> Clip : Duplicate the given clip into the arrangement of this track at the provided destination time and return it. When the type of the clip and the type of the track are incompatible, a runtime error is raised. C++ signature :  TWeakPtr<TPyHandle<AClip>> duplicate_clip_to_arrangement(TTrackPyHandle,TPyHandle<AClip>,double)
- **Live.Track.Track.duplicate_device()** _Built-In_
  > duplicate_device( (Track)arg1, (int)arg2) -> None : Duplicate a device at a given index in the 'devices' list. C++ signature :  void duplicate_device(TTrackPyHandle,int)
- **Live.Track.Track.get_data()** _Built-In_
  > get_data( (Track)arg1, (object)key, (object)default_value) -> object : Get data for the given key, that was previously stored using set_data. C++ signature :  boost::python::api::object get_data(TTrackPyHandle,TString,boost::python::api::object)
- **Live.Track.Track.insert_device()** _Built-In_
  > insert_device( (Track)arg1, (str)DeviceName [, (int)DeviceIndex=-1]) -> LomObject : Add a device at a given index in the 'devices' list. At end if -1. C++ signature :  TWeakPtr<TPyHandleBase> insert_device(TTrackPyHandle,std::__1::basic_string<char, std::__1::char_traits<char>, std::__1::allocator<char>> [,int=-1])
- **Live.Track.Track.jump_in_running_session_clip()** _Built-In_
  > jump_in_running_session_clip( (Track)arg1, (float)arg2) -> None : Jump forward or backward in the currently running Sessionclip (if any) by the specified relative amount in beats. Does nothing if no Session Clip is currently running. C++ signature :  void jump_in_running_session_clip(TTrackPyHandle,double)
- **Live.Track.Track.set_data()** _Built-In_
  > set_data( (Track)arg1, (object)key, (object)value) -> None : Store data for the given key in this object. The data is persistent and will be restored when loading the Live Set. C++ signature :  void set_data(TTrackPyHandle,TString,boost::python::api::object)
- **Live.Track.Track.stop_all_clips()** _Built-In_
  > stop_all_clips( (Track)arg1 [, (bool)Quantized=True]) -> None : Stop running and triggered clip and slots on this track. C++ signature :  void stop_all_clips(TTrackPyHandle [,bool=True])
- **Live.Track.Track.arm** _Property_ — `get, set, observe`
  > Arm the track for recording. Not available for Main- and Send Tracks.
- **Live.Track.Track.arrangement_clips** _Property_RO_ — `get, observe`
  > const access to the list of clips in arrangement viewThe list will be empty for the main, send and group tracks.
- **Live.Track.Track.available_input_routing_channels** _Property_RO_ — `get, observe`
  > Return a list of source channels for input routing.
- **Live.Track.Track.available_input_routing_types** _Property_RO_ — `get, observe`
  > Return a list of source types for input routing.
- **Live.Track.Track.available_output_routing_channels** _Property_RO_ — `get, observe`
  > Return a list of destination channels for output routing.
- **Live.Track.Track.available_output_routing_types** _Property_RO_ — `get, observe`
  > Return a list of destination types for output routing.
- **Live.Track.Track.back_to_arranger** _Property_ — `get, set, observe`
  > Indicates if it's possible to go back to playing back the clips in the Arranger.Setting a value 0 will go back to the Arranger playback. Setting on grouptracks will go back to the Arranger on all grouped tracks.
- **Live.Track.Track.can_be_armed** _Property_RO_ — `get`
  > return True, if this Track has a valid arm property. Not all trackscan be armed (for example return Tracks or the Main Tracks).
- **Live.Track.Track.can_be_frozen** _Property_RO_ — `get`
  > return True, if this Track can be frozen.
- **Live.Track.Track.can_show_chains** _Property_RO_ — `get`
  > return True, if this Track contains a rack instrument device that is capable of showing its chains in session view.
- **Live.Track.Track.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the track.
- **Live.Track.Track.clip_slots** _Property_RO_ — `get, observe`
  > const access to the list of clipslots (see class AClipSlot) for this track.The list will be empty for the main and sendtracks.
- **Live.Track.Track.color** _Property_ — `get, set, observe`
  > Get/set access to the color of the Track (RGB).
- **Live.Track.Track.color_index** _Property_ — `get, set, observe`
  > Get/Set access to the color index of the track. Can be None for no color.
- **Live.Track.Track.current_input_routing** _Property_ — `get, set, observe`
  > Get/Set the name of the current active input routing.When setting a new routing, the new routing must be one of the available ones.
- **Live.Track.Track.current_input_sub_routing** _Property_ — `get, set, observe`
  > Get/Set the current active input sub routing.When setting a new routing, the new routing must be one of the available ones.
- **Live.Track.Track.current_monitoring_state** _Property_ — `get, set, observe`
  > Get/Set the track's current monitoring state.
- **Live.Track.Track.current_output_routing** _Property_ — `get, set, observe`
  > Get/Set the current active output routing.When setting a new routing, the new routing must be one of the available ones.
- **Live.Track.Track.current_output_sub_routing** _Property_ — `get, set, observe`
  > Get/Set the current active output sub routing.When setting a new routing, the new routing must be one of the available ones.
- **Live.Track.Track.devices** _Property_RO_ — `get, observe`
  > Return const access to all available Devices that are present in the TracksDevicechain. This tuple will also include the 'mixer_device' that every Trackalways has.
- **Live.Track.Track.fired_slot_index** _Property_RO_ — `get, observe`
  > const access to the index of the fired (and thus blinking) clipslot in this track.This index is -1 if no slot is fired and -2 if the track's stop button has been fired.
- **Live.Track.Track.fold_state** _Property_ — `get, set`
  > Get/Set whether the track is folded or not. Only available if is_foldable is True.
- **Live.Track.Track.group_track** _Property_RO_ — `get`
  > return the group track if is_grouped.
- **Live.Track.Track.has_audio_input** _Property_RO_ — `get, observe`
  > return True, if this Track can be feed with an Audio signal. This istrue for all Audio Tracks.
- **Live.Track.Track.has_audio_output** _Property_RO_ — `get, observe`
  > return True, if this Track sends out an Audio signal. This istrue for all Audio Tracks, and MIDI tracks with an Instrument.
- **Live.Track.Track.has_midi_input** _Property_RO_ — `get, observe`
  > return True, if this Track can be feed with an Audio signal. This istrue for all MIDI Tracks.
- **Live.Track.Track.has_midi_output** _Property_RO_ — `get, observe`
  > return True, if this Track sends out MIDI events. This istrue for all MIDI Tracks with no Instruments.
- **Live.Track.Track.implicit_arm** _Property_ — `get, set, observe`
  > Arm the track for recording. When The track is implicitly armed, it showsin a weaker color in the live GUI and is not saved in the set.
- **Live.Track.Track.input_meter_left** _Property_RO_ — `get, observe`
  > Momentary value of left input channel meter, 0.0 to 1.0. For Audio Tracks only.
- **Live.Track.Track.input_meter_level** _Property_RO_ — `get, observe`
  > Return the MIDI or Audio meter value of the Tracks input, depending on thetype of the Track input. Meter values (MIDI or Audio) are always scaledfrom 0.0 to 1.0.
- **Live.Track.Track.input_meter_right** _Property_RO_ — `get, observe`
  > Momentary value of right input channel meter, 0.0 to 1.0. For Audio Tracks only.
- **Live.Track.Track.input_routing_channel** _Property_ — `get, set, observe`
  > Get and set the current source channel for input routing.Raises ValueError if the type isn't one of the current values inavailable_input_routing_channels.
- **Live.Track.Track.input_routing_type** _Property_ — `get, set, observe`
  > Get and set the current source type for input routing.Raises ValueError if the type isn't one of the current values inavailable_input_routing_types.
- **Live.Track.Track.input_routings** _Property_RO_ — `get, observe`
  > Const access to the list of available input routings.
- **Live.Track.Track.input_sub_routings** _Property_RO_ — `get, observe`
  > Return a list of all available input sub routings.
- **Live.Track.Track.is_foldable** _Property_RO_ — `get`
  > return True if the track can be (un)folded to hide/reveal contained tracks.
- **Live.Track.Track.is_frozen** _Property_RO_ — `get, observe`
  > return True if this Track is currently frozen. No changes should be applied to the track's devices or clips while it is frozen.
- **Live.Track.Track.is_grouped** _Property_RO_ — `get`
  > return True if this Track is current part of a group track.
- **Live.Track.Track.is_part_of_selection** _Property_RO_ — `get`
  > return False if the track is not selected.
- **Live.Track.Track.is_showing_chains** _Property_ — `get, set, observe`
  > Get/Set whether a track with a rack device is showing its chains in session view.
- **Live.Track.Track.is_visible** _Property_RO_ — `get`
  > return False if the track is hidden within a folded group track.
- **Live.Track.Track.mixer_device** _Property_RO_ — `get`
  > Return access to the special Device that every Track has: This Device containsthe Volume, Pan, Sendamounts, and Crossfade assignment parameters.
- **Live.Track.Track.mute** _Property_ — `get, set, observe`
  > Mute/unmute the track.
- **Live.Track.Track.muted_via_solo** _Property_RO_ — `get, observe`
  > Returns true if the track is muted because another track is soloed.
- **Live.Track.Track.name** _Property_ — `get, set, observe`
  > Read/write access to the name of the Track, as visible in the track header.
- **Live.Track.Track.output_meter_left** _Property_RO_ — `get, observe`
  > Momentary value of left output channel meter, 0.0 to 1.0.For tracks with audio output only.
- **Live.Track.Track.output_meter_level** _Property_RO_ — `get, observe`
  > Return the MIDI or Audio meter value of the Track output (behind themixer_device), depending on the type of the Track input, this can be a MIDIor Audio meter. Meter values (MIDI or Audio) are always scaled from 0.0 to 1.0.
- **Live.Track.Track.output_meter_right** _Property_RO_ — `get, observe`
  > Momentary value of right output channel meter, 0.0 to 1.0.For tracks with audio output only.
- **Live.Track.Track.output_routing_channel** _Property_ — `get, set, observe`
  > Get and set the current destination channel for output routing.Raises ValueError if the channel isn't one of the current values inavailable_output_routing_channels.
- **Live.Track.Track.output_routing_type** _Property_ — `get, set, observe`
  > Get and set the current destination type for output routing.Raises ValueError if the type isn't one of the current values inavailable_output_routing_types.
- **Live.Track.Track.output_routings** _Property_RO_ — `get, observe`
  > Const access to the list of all available output routings.
- **Live.Track.Track.output_sub_routings** _Property_RO_ — `get, observe`
  > Return a list of all available output sub routings.
- **Live.Track.Track.performance_impact** _Property_RO_ — `get, observe`
  > Reports the performance impact of this track.
- **Live.Track.Track.playing_slot_index** _Property_RO_ — `get, observe`
  > const access to the index of the currently playing clip in the track.Will be -1 when no clip is playing.
- **Live.Track.Track.solo** _Property_ — `get, set, observe`
  > Get/Set the solo status of the track. Note that this will not disable thesolo state of any other track. If you want exclusive solo, you have to disable the solo state of the other Tracks manually.
- **Live.Track.Track.take_lanes** _Property_RO_ — `get, observe`
  > returns the take lanes.
- **Live.Track.Track.view** _Property_RO_ — `get`
  > Representing the view aspects of a Track.

#### Live.Track.Track.monitoring_states

  - Enum (3): `IN=IN`, `AUTO=AUTO`, `OFF=OFF`

#### Live.Track.Track.View

> Representing the view aspects of a Track.

- **Live.Track.Track.View.select_instrument()** _Built-In_
  > select_instrument( (View)arg1) -> bool : Selects the track's instrument if it has one. C++ signature :  bool select_instrument(TPyViewData<ATrack>)
- **Live.Track.Track.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the track view.
- **Live.Track.Track.View.device_insert_mode** _Property_ — `get, set, observe`
  > Get/Listen the device insertion mode of the track.  By default, it will insert devices at the end, but it can be changed to make it relative to current selection.
- **Live.Track.Track.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the track is shown collapsed in the arranger view.
- **Live.Track.Track.View.selected_device** _Property_RO_ — `get, observe`
  > Get/Set/Listen the insertion mode of the device.  While in insertion mode, loading new devices from the browser will place devices at the selected position.

## Live.TuningSystem


### Live.TuningSystem.PitchClassAndOctave

> This class represents a PitchClassAndOctave type.

- **Live.TuningSystem.PitchClassAndOctave.index_in_octave** _Property_RO_ — `get`
  > A PitchClassAndOctave's index within the pseudo octave.
- **Live.TuningSystem.PitchClassAndOctave.octave** _Property_RO_ — `get`
  > A PitchClassAndOctave's octave.

### Live.TuningSystem.ReferencePitch

> This class represents a ReferencePitch type.

- **Live.TuningSystem.ReferencePitch.frequency** _Property_RO_ — `get`
  > A ReferencePitch's frequency in Hz.
- **Live.TuningSystem.ReferencePitch.index_in_octave** _Property_RO_ — `get`
  > A ReferencePitch's index within the pseudo octave.
- **Live.TuningSystem.ReferencePitch.octave** _Property_RO_ — `get`
  > A ReferencePitch's octave.

### Live.TuningSystem.TuningSystem

> Represents a Tuning System and its properties.

- **Live.TuningSystem.TuningSystem.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the TuningSystem.
- **Live.TuningSystem.TuningSystem.highest_note** _Property_ — `get, set, observe`
  > Get/Set the highest note of the current tuning system, where the first entry isthe index within the pseudo octave and the second entry is the octave.
- **Live.TuningSystem.TuningSystem.lowest_note** _Property_ — `get, set, observe`
  > Get/Set the lowest note of the current tuning system, where the first entry isthe index within the pseudo octave and the second entry is the octave.
- **Live.TuningSystem.TuningSystem.name** _Property_ — `get, set, observe`
  > Get/Set the name of the currently active tuning system.
- **Live.TuningSystem.TuningSystem.note_tunings** _Property_ — `get, set, observe`
  > Get/Set the currently active tuning system's note tunings, specified in Cents, where 100 Cents is one semi-tone in equal temperament.
- **Live.TuningSystem.TuningSystem.number_of_notes_in_pseudo_octave** _Property_RO_ — `get`
  > Get the number of notes in the pseudo octave.
- **Live.TuningSystem.TuningSystem.pseudo_octave_in_cents** _Property_RO_ — `get`
  > Get the pseudo octave in cents for the currently active tuning system.
- **Live.TuningSystem.TuningSystem.reference_pitch** _Property_ — `get, set, observe`
  > Get/Set the reference pitch the currently active tuning system.

## Live.WavetableDevice


### Live.WavetableDevice.EffectMode

  - Enum (4): `none=none`, `frequency_modulation=frequency_modulation`, `sync_and_pulse_width=sync_and_pulse_width`, `warp_and_fold=warp_and_fold`

### Live.WavetableDevice.FilterRouting

  - Enum (3): `serial=serial`, `parallel=parallel`, `split=split`

### Live.WavetableDevice.ModulationSource

  - Enum (11): `amp_envelope=amp_envelope`, `envelope_2=envelope_2`, `envelope_3=envelope_3`, `lfo_1=lfo_1`, `lfo_2=lfo_2`, `midi_velocity=midi_velocity`, `midi_note=midi_note`, `midi_pitch_bend=midi_pitch_bend`, `midi_channel_pressure=midi_channel_pressure`, `midi_mod_wheel=midi_mod_wheel`, `midi_random=midi_random`

### Live.WavetableDevice.UnisonMode

  - Enum (7): `none=none`, `classic=classic`, `slow_shimmer=slow_shimmer`, `fast_shimmer=fast_shimmer`, `phase_sync=phase_sync`, `position_spread=position_spread`, `random_note=random_note`

### Live.WavetableDevice.VoiceCount

  - Enum (8): `two=two`, `three=three`, `four=four`, `five=five`, `six=six`, `seven=seven`, `eight=eight`, `sixteen=sixteen`

### Live.WavetableDevice.Voicing

  - Enum (2): `mono=mono`, `poly=poly`

### Live.WavetableDevice.WavetableDevice

> This class represents a Wavetable device.

- **Live.WavetableDevice.WavetableDevice.add_parameter_to_modulation_matrix()** _Built-In_
  > add_parameter_to_modulation_matrix( (WavetableDevice)self, (DeviceParameter)parameter) -> int : Add a non-pitch parameter to the modulation matrix. C++ signature :  int add_parameter_to_modulation_matrix(TWavetableDevicePyHandle,TPyHandle<ATimeableValue>)
- **Live.WavetableDevice.WavetableDevice.get_modulation_target_parameter_name()** _Built-In_
  > get_modulation_target_parameter_name( (WavetableDevice)self, (int)target_index) -> str : Get the parameter name of the modulation target at the given index. C++ signature :  TString get_modulation_target_parameter_name(TWavetableDevicePyHandle,int)
- **Live.WavetableDevice.WavetableDevice.get_modulation_value()** _Built-In_
  > get_modulation_value( (WavetableDevice)self, (int)target_index, (int)source) -> float : Get the value of a modulation amount for the given target-source connection. C++ signature :  float get_modulation_value(TWavetableDevicePyHandle,int,int)
- **Live.WavetableDevice.WavetableDevice.is_parameter_modulatable()** _Built-In_
  > is_parameter_modulatable( (WavetableDevice)self, (DeviceParameter)parameter) -> bool : Indicate whether the parameter is modulatable. Note that pitch parameters only exist in python and must be handled there. C++ signature :  bool is_parameter_modulatable(TWavetableDevicePyHandle,TPyHandle<ATimeableValue>)
- **Live.WavetableDevice.WavetableDevice.save_preset_to_compare_ab_slot()** _Built-In_
  > save_preset_to_compare_ab_slot( (Device)arg1) -> None : Saves the current state of the device to the compare AB slot. Only relevant if can_compare_ab, otherwise throws. C++ signature :  void save_preset_to_compare_ab_slot(TPyHandle<ADevice>)
- **Live.WavetableDevice.WavetableDevice.set_modulation_value()** _Built-In_
  > set_modulation_value( (WavetableDevice)self, (int)target_index, (int)source, (float)value) -> None : Set the value of a modulation amount for the given target-source connection. C++ signature :  void set_modulation_value(TWavetableDevicePyHandle,int,int,float)
- **Live.WavetableDevice.WavetableDevice.store_chosen_bank()** _Built-In_
  > store_chosen_bank( (Device)arg1, (int)arg2, (int)arg3) -> None : Set the selected bank in the device for persistency. C++ signature :  void store_chosen_bank(TPyHandle<ADevice>,int,int)
- **Live.WavetableDevice.WavetableDevice.can_compare_ab** _Property_RO_ — `get`
  > Returns true if the Device has the capability to AB compare.
- **Live.WavetableDevice.WavetableDevice.can_have_chains** _Property_RO_ — `get`
  > Returns true if the device is a rack.
- **Live.WavetableDevice.WavetableDevice.can_have_drum_pads** _Property_RO_ — `get`
  > Returns true if the device is a drum rack.
- **Live.WavetableDevice.WavetableDevice.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the Device.
- **Live.WavetableDevice.WavetableDevice.class_display_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class name as displayed in Live's browser and device chain
- **Live.WavetableDevice.WavetableDevice.class_name** _Property_RO_ — `get`
  > Return const access to the name of the device's class.
- **Live.WavetableDevice.WavetableDevice.filter_routing** _Property_ — `get, set, observe`
  > Return the current filter routing.
- **Live.WavetableDevice.WavetableDevice.is_active** _Property_RO_ — `get, observe`
  > Return const access to whether this device is active. This will be false bothwhen the device is off and when it's inside a rack device which is off.
- **Live.WavetableDevice.WavetableDevice.is_using_compare_preset_b** _Property_ — `get, set, observe`
  > Returns whether the Device has loaded the preset in compare slot B. Only relevant if can_compare_ab, otherwise errors.
- **Live.WavetableDevice.WavetableDevice.latency_in_ms** _Property_RO_ — `get, observe`
  > Returns the latency of the device in ms.
- **Live.WavetableDevice.WavetableDevice.latency_in_samples** _Property_RO_ — `get, observe`
  > Returns the latency of the device in samples.
- **Live.WavetableDevice.WavetableDevice.mono_poly** _Property_ — `get, set, observe`
  > Return the current voicing mode.
- **Live.WavetableDevice.WavetableDevice.name** _Property_ — `get, set, observe`
  > Return access to the name of the device.
- **Live.WavetableDevice.WavetableDevice.oscillator_1_effect_mode** _Property_ — `get, set, observe`
  > Return the current effect mode of the oscillator 1.
- **Live.WavetableDevice.WavetableDevice.oscillator_1_wavetable_category** _Property_ — `get, set, observe`
  > Return the current wavetable category of the oscillator 1.
- **Live.WavetableDevice.WavetableDevice.oscillator_1_wavetable_index** _Property_ — `get, set, observe`
  > Return the current wavetable index of the oscillator 1.
- **Live.WavetableDevice.WavetableDevice.oscillator_1_wavetables** _Property_RO_ — `get, observe`
  > Get a vector of oscillator 1's wavetable names.
- **Live.WavetableDevice.WavetableDevice.oscillator_2_effect_mode** _Property_ — `get, set, observe`
  > Return the current effect mode of the oscillator 2.
- **Live.WavetableDevice.WavetableDevice.oscillator_2_wavetable_category** _Property_ — `get, set, observe`
  > Return the current wavetable category of the oscillator 2.
- **Live.WavetableDevice.WavetableDevice.oscillator_2_wavetable_index** _Property_ — `get, set, observe`
  > Return the current wavetable index of the oscillator 2.
- **Live.WavetableDevice.WavetableDevice.oscillator_2_wavetables** _Property_RO_ — `get, observe`
  > Get a vector of oscillator 2's wavetable names.
- **Live.WavetableDevice.WavetableDevice.oscillator_wavetable_categories** _Property_RO_ — `get`
  > Get a vector of the available wavetable categories.
- **Live.WavetableDevice.WavetableDevice.parameters** _Property_RO_ — `get, observe`
  > Const access to the list of available automatable parameters for this device.
- **Live.WavetableDevice.WavetableDevice.poly_voices** _Property_ — `get, set, observe`
  > Return the current number of polyphonic voices. Uses the VoiceCount enumeration.
- **Live.WavetableDevice.WavetableDevice.type** _Property_RO_ — `get`
  > Return the type of the device.
- **Live.WavetableDevice.WavetableDevice.unison_mode** _Property_ — `get, set, observe`
  > Return the current unison mode.
- **Live.WavetableDevice.WavetableDevice.unison_voice_count** _Property_ — `get, set, observe`
  > Return the current number of unison voices.
- **Live.WavetableDevice.WavetableDevice.view** _Property_RO_ — `get`
  > Representing the view aspects of a device.
- **Live.WavetableDevice.WavetableDevice.visible_modulation_target_names** _Property_RO_ — `get, observe`
  > Get the names of all the visible modulation targets.

#### Live.WavetableDevice.WavetableDevice.View

> Representing the view aspects of a device.

- **Live.WavetableDevice.WavetableDevice.View.canonical_parent** _Property_RO_ — `get`
  > Get the canonical parent of the View.
- **Live.WavetableDevice.WavetableDevice.View.is_collapsed** _Property_ — `get, set, observe`
  > Get/Set/Listen if the device is shown collapsed in the device chain.
