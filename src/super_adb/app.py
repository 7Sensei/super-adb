import customtkinter as ctk

from super_adb.services.adb_service import SubprocessAdbService
from super_adb.viewmodels.main_viewmodel import MainViewModel
from super_adb.views.dispatcher import TkDispatcher
from super_adb.views.main_view import MainView


def main() -> None:
    ctk.set_appearance_mode("Light")
    root = ctk.CTk()
    root.title("Super-ADB v2.5")
    root.geometry("1000x650")

    dispatcher = TkDispatcher(root)
    viewmodel = MainViewModel(SubprocessAdbService(), dispatcher)
    view = MainView(root, viewmodel)
    view.pack(fill="both", expand=True)

    def close_application() -> None:
        dispatcher.close()
        viewmodel.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close_application)
    root.mainloop()
