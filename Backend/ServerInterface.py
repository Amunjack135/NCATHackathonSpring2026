import dearpygui.dearpygui as dpg
import screeninfo
import threading
import time
import typing
import uuid

import CustomMethodsVI.Connection as Connection
import CustomMethodsVI.Logger as Logger

import Simulation


BG_COLOR_0: tuple[int, int, int, int] = (0x22, 0x22, 0x22, 0xFF)
COLOR_RED: tuple[int, int, int, int] = (0xFF, 0x00, 0x00, 0xFF)
COLOR_GREEN: tuple[int, int, int, int] = (0x00, 0xFF, 0x00, 0xFF)
COLOR_WHITE: tuple[int, int, int, int] = (0xFF, 0xFF, 0xFF, 0xFF)

FIT_OVERHEAD: float = 1.25


def get_monitor_position(name: typing.Optional[str] = None) -> tuple[str, int, int]:
	if isinstance(name, str):
		for monitor in screeninfo.get_monitors():
			if monitor.name == name:
				return monitor.name, monitor.x, monitor.y

		return get_monitor_position(None)
	else:
		max_size: int = 0
		max_monitor: screeninfo.Monitor = ...

		for monitor in screeninfo.get_monitors():
			size: int = monitor.width * monitor.height

			if size > max_size:
				max_monitor = monitor

		return max_monitor.name, max_monitor.x, max_monitor.y


def init(app: Connection.FlaskSocketioServer, logger: Logger.Logger, simulation: Simulation.MyOilFieldSimulation) -> typing.Callable[[], None]:
	def closer() -> None:
		event.set()
		gui_thread.join()

	event: threading.Event = threading.Event()
	gui_thread: threading.Thread = threading.Thread(target=gui_main, args=(event, logger, simulation))
	gui_thread.start()
	return closer


def gui_main(halt_event: threading.Event, logger: Logger.Logger, simulation: Simulation.MyOilFieldSimulation) -> None:
	def set_monitor(sender: int, data: str) -> None:
		target, x, y = get_monitor_position(data)
		dpg.set_viewport_pos([x, y])

	def tick() -> None:
		nonlocal widget_parent
		row_height: int = round(dpg.get_viewport_height() * 0.25)
		spacer: int = round(dpg.get_viewport_height() * 0.05)
		now: float = time.perf_counter()

		for pump in simulation.pumps:
			widget_id: str = f'pump.{pump.uuid}'

			if not dpg.does_item_exist(widget_id):
				if len(pump_data) % 2 == 0:
					widget_parent = dpg.add_table_row(parent=pump_list, height=row_height)

				with dpg.table_cell(parent=widget_parent, tag=widget_id):
					with dpg.table(resizable=False, policy=dpg.mvTable_SizingStretchProp, header_row=True):
						dpg.add_table_column(init_width_or_weight=1, label='Overview')
						dpg.add_table_column(init_width_or_weight=2, label='Metrics 01')
						dpg.add_table_column(init_width_or_weight=2, label='Metrics 02')

						with dpg.table_row():
							text: int = dpg.add_text(f'Pump ID:\n{pump.uuid}', color=COLOR_GREEN if pump.is_running else COLOR_RED)

						with dpg.table_row():
							with dpg.table(resizable=False, policy=dpg.mvTable_SizingStretchProp, header_row=False):
								dpg.add_table_column(init_width_or_weight=1)
								dpg.add_table_column(init_width_or_weight=3)
								dpg.add_table_column(init_width_or_weight=1)

								with dpg.table_row():
									dpg.add_spacer()

									with dpg.table_cell():
										dpg.add_button(label='Start Pump', width=-1, callback=lambda s, d, *, p=pump: p.start_pump())
										dpg.add_button(label='Stop Pump', width=-1, callback=lambda s, d, *, p=pump: p.stop_pump())
										dpg.add_button(label='Fail Pump', width=-1, callback=lambda s, d, *, p=pump: p.move_to_error_state())
										dpg.add_spacer(height=spacer)
										dpg.add_separator()
										dpg.add_spacer(height=spacer)
										temperature_text: int = dpg.add_text('Temperature: N/A')
										pressure_text: int = dpg.add_text('Pressure: N/A')
										flow_rate_text: int = dpg.add_text('Flow Rate: N/A')
										rpm_text: int = dpg.add_text('RPM: N/A')
										load_percent_text: int = dpg.add_text('Load %: N/A')
										vibration_text: int = dpg.add_text('Vibration: N/A')
										error_tick_text: int = dpg.add_text('Error Tick: N/A')

							with dpg.plot(label='Pump Metrics 0', width=-1, height=round(row_height * 0.95)):
								dpg.add_plot_legend(outside=True, horizontal=True)
								xaxis0: int = dpg.add_plot_axis(dpg.mvXAxis, label='Time (seconds)')
								yaxis0: int = dpg.add_plot_axis(dpg.mvYAxis, label='Temperature (C)')
								yaxis1: int = dpg.add_plot_axis(dpg.mvYAxis2, label='Pressure (Bar)')
								yaxis2: int = dpg.add_plot_axis(dpg.mvYAxis3, label='Flow Rate (CFM)')
								pump_temperature: int = dpg.add_stem_series([], [], label='Pump Temperature', parent=yaxis0)
								pump_pressure: int = dpg.add_stem_series([], [], label='Pump Pressure', parent=yaxis1)
								pump_flow_rate: int = dpg.add_stem_series([], [], label='Pump Flow Rate', parent=yaxis2)

							with dpg.plot(label='Pump Metrics 1', width=-1, height=round(row_height * 0.95)):
								dpg.add_plot_legend(outside=True, horizontal=True)
								xaxis1: int = dpg.add_plot_axis(dpg.mvXAxis, label='Time (seconds)')
								yaxis3: int = dpg.add_plot_axis(dpg.mvYAxis, label='RPM (rpm)')
								yaxis4: int = dpg.add_plot_axis(dpg.mvYAxis2, label='Load (%)')
								yaxis5: int = dpg.add_plot_axis(dpg.mvYAxis3, label='Vibration (Hz)')
								pump_rpm: int = dpg.add_stem_series([], [], label='Pump RPM', parent=yaxis3)
								pump_load: int = dpg.add_stem_series([], [], label='Pump Load %', parent=yaxis4)
								pump_vibration: int = dpg.add_stem_series([], [], label='Pump Vibration', parent=yaxis5)

				pump_data[pump.uuid] = (text, pump_temperature, pump_pressure, pump_flow_rate, pump_rpm, pump_load, pump_vibration, {
					0: (pump.temperature, pump.pressure, pump.flow_rate, pump.rpm, pump.load_percent, pump.vibration)
				}, (xaxis0, xaxis1, yaxis0, yaxis1, yaxis2, yaxis3, yaxis4, yaxis5), (temperature_text, pressure_text, flow_rate_text, rpm_text, load_percent_text, vibration_text, error_tick_text))

			else:
				text, pump_temperature, pump_pressure, pump_flow_rate, pump_rpm, pump_load, pump_vibration, metrics, axes, texts = pump_data[pump.uuid]
				xaxis0, xaxis1, yaxis0, yaxis1, yaxis2, yaxis3, yaxis4, yaxis5 = axes
				temperature_text, pressure_text, flow_rate_text, rpm_text, load_percent_text, vibration_text, error_tick_text = texts
				metrics[now - start_time] = (pump.temperature, pump.pressure, pump.flow_rate, pump.rpm, pump.load_percent, pump.vibration)
				times: list[float] = list(metrics.keys())
				max_time: float = max(times) + 1
				min_time: float = max(-1., max_time - 30)
				closed_metrics: tuple[float, ...] = tuple(timestamp for timestamp in metrics if timestamp < min_time)
				dpg.configure_item(text, color=COLOR_GREEN if pump.is_running else COLOR_RED)
				dpg.configure_item(error_tick_text, color=COLOR_WHITE if pump.__error_ratio__ == 0 else COLOR_RED)

				for closed in closed_metrics:
					del metrics[closed]

				dpg.set_value(pump_temperature, [times, temperatures := [metric[0] for timestamp, metric in metrics.items() if timestamp]])
				dpg.set_value(pump_pressure, [times, pressures := [metric[1] for metric in metrics.values()]])
				dpg.set_value(pump_flow_rate, [times, flow_rates := [metric[2] for metric in metrics.values()]])
				dpg.set_value(pump_rpm, [times, rpms := [metric[3] for metric in metrics.values()]])
				dpg.set_value(pump_load, [times, load_percents := [metric[4] for metric in metrics.values()]])
				dpg.set_value(pump_vibration, [times, vibrations := [metric[5] for metric in metrics.values()]])

				dpg.set_axis_limits(xaxis0, min_time, max_time)
				dpg.set_axis_limits(xaxis1, min_time, max_time)

				dpg.set_axis_limits(yaxis0, -1, max(temperatures) * FIT_OVERHEAD)
				dpg.set_axis_limits(yaxis1, -1, max(pressures) * FIT_OVERHEAD)
				dpg.set_axis_limits(yaxis2, -1, max(flow_rates) * FIT_OVERHEAD)

				dpg.set_axis_limits(yaxis3, -1, max(rpms) * FIT_OVERHEAD)
				dpg.set_axis_limits(yaxis4, -1, max(load_percents) * FIT_OVERHEAD)
				dpg.set_axis_limits(yaxis5, -1, max(vibrations) * FIT_OVERHEAD)

				dpg.set_value(temperature_text, f'Temperature: {pump.temperature:.2f} C')
				dpg.set_value(pressure_text, f'Pressure: {pump.pressure:.2f} Bar')
				dpg.set_value(flow_rate_text, f'Flow Rate: {pump.flow_rate:.2f} CFM')
				dpg.set_value(rpm_text, f'RPM: {pump.rpm:.2f} RPM')
				dpg.set_value(load_percent_text, f'Load: {pump.load_percent:.2f} %')
				dpg.set_value(vibration_text, f'Vibration: {pump.vibration:.2f} Hz')
				dpg.set_value(error_tick_text, f'Error Tick: {pump.__error_ratio__}')

	dpg.create_context()
	dpg.create_viewport(title='Pipe Dot Net Server Monitor')
	dpg.setup_dearpygui()
	dpg.show_viewport()
	dpg.set_viewport_vsync(True)
	dpg.set_viewport_resizable(False)
	dpg.set_viewport_decorated(False)

	with dpg.theme() as window_theme:
		with dpg.theme_component(dpg.mvAll):
			dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG_COLOR_0, category=dpg.mvThemeCat_Core)
			dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
			dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
			dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)

	with dpg.handler_registry():
		dpg.add_key_release_handler(dpg.mvKey_Escape, callback=lambda: halt_event.set())

	with dpg.window(tag='PrimaryWindow'):
		dpg.bind_font('Font0')

		dpg.add_listbox([monitor.name for monitor in screeninfo.get_monitors()], label='Display', width=-1, callback=set_monitor)

		with dpg.table(resizable=False, policy=dpg.mvTable_SizingStretchProp, header_row=False) as pump_list:
			dpg.add_table_column(init_width_or_weight=1)
			dpg.add_table_column(init_width_or_weight=1)

	dpg.bind_item_theme('PrimaryWindow', window_theme)
	dpg.set_primary_window('PrimaryWindow', True)
	dpg.configure_item('PrimaryWindow', no_scrollbar=False, no_scroll_with_mouse=False)
	dpg.toggle_viewport_fullscreen()
	start_time: float = time.perf_counter()
	time_point_1: float = start_time
	pump_data: dict[uuid.UUID, tuple[int | dict[float, tuple[float, ...]] | tuple[int, ...], ...]] = {}
	widget_parent: int = ...

	while not halt_event.is_set() and dpg.is_dearpygui_running():
		time_point_2: float = time.perf_counter()

		if (time_point_2 - time_point_1) >= 1:
			time_point_1 = time_point_2
			tick()

		dpg.render_dearpygui_frame()

	dpg.destroy_context()


__all__: list[str] = ['init']
