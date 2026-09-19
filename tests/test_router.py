from dera.tasks.router import IntentRouter


class Model:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return '{"intent": "explain_slow_computer"}'


def test_startup_language_overrides_model_misclassification() -> None:
    assert IntentRouter(Model()).route("Why does my computer take so long to start?") == "diagnose_startup_applications"


def test_slow_computer_language_routes_deterministically() -> None:
    assert IntentRouter(Model()).route("My computer is slow") == "investigate_slow_computer"


def test_natural_performance_and_storage_variations_route_safely() -> None:
    router = IntentRouter(Model())
    assert router.route("What's slowing down my PC?") == "investigate_slow_computer"
    assert router.route("My laptop feels laggy") == "investigate_slow_computer"
    assert router.route("Can you clear space in my Downloads?") == "review_downloads_proposals"


def test_explanation_and_startup_variations_route_safely() -> None:
    router = IntentRouter(Model())
    assert router.route("Explain my computer findings in simpler terms") == "explain_slow_computer"
    assert router.route("What launches at login?") == "diagnose_startup_applications"


def test_crash_language_routes_to_the_read_only_crash_investigation() -> None:
    router = IntentRouter(Model())
    assert router.route("Chrome keeps crashing") == "investigate_application_crash"
    assert router.route("Why did Discord close unexpectedly?") == "investigate_application_crash"


def test_largest_folder_language_routes_to_read_only_home_inspection() -> None:
    router = IntentRouter(Model())
    assert router.route("What is my biggest folder?") == "inspect_user_folders"
    assert router.route("What is taking up space on my PC?") == "inspect_user_folders"
