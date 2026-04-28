from flask import Flask

from .assets import asset_css_urls, asset_url
from .config import Config
from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)

    from .main.routes import main_bp
    from .api.routes import api_bp
    from .provider_pages import provider_bp
    from .settings import settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(provider_bp)

    app.jinja_env.globals["asset_url"] = asset_url
    app.jinja_env.globals["asset_css_urls"] = asset_css_urls

    @app.cli.command("init-db")
    def init_db():
        with app.app_context():
            db.create_all()
            _seed_learning_defaults()
            print("Database initialized.")

    return app


def _seed_learning_defaults():
    from .models import SavedModel, SavedPrompt

    if not SavedModel.query.filter_by(name="gpt-4.1-mini").first():
        db.session.add(
            SavedModel(
                name="gpt-4.1-mini",
                description="General purpose starter model for OpenAI API experiments.",
            )
        )

    if not SavedPrompt.query.filter_by(title="Helpful Python tutor").first():
        db.session.add(
            SavedPrompt(
                title="Helpful Python tutor",
                description="Explains answers clearly while helping you learn the code.",
                prompt_text=(
                    "You are a helpful Python tutor. Explain concepts simply, show concise examples, "
                    "and point out practical next steps."
                ),
            )
        )

    db.session.commit()
