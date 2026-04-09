import framebuf

from sh1106 import SH1106_I2C


def _format_value(value, suffix, precision=1):
    if value is None:
        return "--"
    if precision == 0:
        return "%d%s" % (int(value), suffix)
    return ("%0." + str(precision) + "f%s") % (value, suffix)


def _text_width(text, scale=1):
    return len(text) * 8 * scale


def _largest_scale(text, max_width, max_scale):
    for scale in range(max_scale, 0, -1):
        if _text_width(text, scale) <= max_width:
            return scale
    return 1


def _draw_text(oled, text, x, y, scale=1):
    if scale <= 1:
        oled.text(text, x, y)
        return

    width = len(text) * 8
    buffer = bytearray(width)
    temp = framebuf.FrameBuffer(buffer, width, 8, framebuf.MONO_HLSB)
    temp.fill(0)
    temp.text(text, 0, 0, 1)

    for src_y in range(8):
        for src_x in range(width):
            if temp.pixel(src_x, src_y):
                oled.fill_rect(x + src_x * scale, y + src_y * scale, scale, scale, 1)


class StatusDisplay:
    def __init__(self, i2c, config):
        self.config = config
        self.display = SH1106_I2C(
            config.OLED_WIDTH,
            config.OLED_HEIGHT,
            i2c,
            addr=config.OLED_ADDR,
        )

    def _header_text(self, footer_text):
        if getattr(self.config, "OLED_SHOW_MODE", False) and footer_text == "DISPLAY ONLY":
            return getattr(self.config, "OLED_MODE_LABEL", self.config.RUN_MODE.upper())
        return footer_text

    def _render_data_only(self, values):
        oled = self.display

        temperature_text = _format_value(values.get("temperature_c"), "C", 1)
        humidity_text = _format_value(values.get("humidity_pct"), "%", 0)
        light_text = _format_value(values.get("light_lux"), "lux", 0)

        temperature_scale = _largest_scale(temperature_text, 124, 3)
        humidity_scale = _largest_scale(humidity_text, 60, 2)
        light_scale = _largest_scale(light_text, 60, 1)

        _draw_text(
            oled,
            temperature_text,
            max(0, (128 - _text_width(temperature_text, temperature_scale)) // 2),
            2,
            temperature_scale,
        )
        _draw_text(
            oled,
            humidity_text,
            max(0, (64 - _text_width(humidity_text, humidity_scale)) // 2),
            42,
            humidity_scale,
        )
        _draw_text(
            oled,
            light_text,
            64 + max(0, (64 - _text_width(light_text, light_scale)) // 2),
            46,
            light_scale,
        )

    def render(self, values, footer_text):
        oled = self.display
        oled.fill(0)

        if getattr(self.config, "OLED_LAYOUT", "status") == "data_only":
            self._render_data_only(values)
            oled.show()
            return

        header_text = self._header_text(footer_text)[:16]
        oled.text(header_text, max(0, (128 - _text_width(header_text)) // 2), 0)
        oled.hline(0, 10, 128, 1)

        temperature_text = _format_value(values.get("temperature_c"), "C", 1)
        temperature_scale = _largest_scale(temperature_text, 120, 3)
        _draw_text(
            oled,
            temperature_text,
            max(0, (128 - _text_width(temperature_text, temperature_scale)) // 2),
            12,
            temperature_scale,
        )

        oled.hline(0, 38, 128, 1)
        oled.vline(63, 39, 25, 1)

        humidity_text = _format_value(values.get("humidity_pct"), "", 0)
        light_text = _format_value(values.get("light_lux"), "", 0)
        humidity_scale = _largest_scale(humidity_text, 52, 2)
        light_scale = _largest_scale(light_text, 52, 2)

        oled.text("HUMID", 8, 41)
        oled.text("LUX", 86, 41)
        _draw_text(
            oled,
            humidity_text,
            6 + max(0, (52 - _text_width(humidity_text, humidity_scale)) // 2),
            49,
            humidity_scale,
        )
        _draw_text(
            oled,
            light_text,
            70 + max(0, (52 - _text_width(light_text, light_scale)) // 2),
            49,
            light_scale,
        )
        oled.show()
