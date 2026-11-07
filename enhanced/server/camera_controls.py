"""Build 654420 camera defaults; integrates without modifying client archives."""
import functools
import json

# OptionManager.<cinit>: height/zoom/pro zoom/speed/swing defaults = 10,
# slider maxima = 20. Camera index 1 is Tele (index 0 is fixed Tele Broadcast).
# CamDetail follows OptionCameraSettingScreen's own default (customization OFF).
CAMERA_DEFAULTS = dict(Camera=1, CamDetail=0, CamHeight=10, CamZoom=10,
                       CamProZoom=10, CamProSpeed=10, CamProSwing=10)


def normalize_camera(value):
    result = dict(value) if isinstance(value, dict) else {}
    for key, default in CAMERA_DEFAULTS.items():
        maximum = 6 if key == 'Camera' else 1 if key == 'CamDetail' else 20
        if type(result.get(key)) is not int or not 0 <= result[key] <= maximum:
            result[key] = default
    return result


def install(hc):
    if getattr(hc, '_camera_controls_installed', False):
        return
    original_account_option = hc.account_option
    original_save_option = hc.ep_account_option

    @functools.wraps(original_account_option)
    def account_option():
        option = original_account_option()
        option['cameraOption'] = normalize_camera(option.get('cameraOption'))
        return option

    @functools.wraps(original_save_option)
    def save_option(query, body):
        request = json.loads(body or b'{}')
        # A partial camera update must not erase the other camera sliders.
        camera = account_option()['cameraOption']
        incoming = request.get('cameraOption')
        if isinstance(incoming, dict):
            camera.update(incoming)
        request['cameraOption'] = normalize_camera(camera)
        return original_save_option(query, json.dumps(request).encode())

    hc.account_option = account_option
    hc.ep_account_option = save_option
    hc.ENDPOINTS['/account/option'] = save_option
    hc._camera_controls_installed = True
