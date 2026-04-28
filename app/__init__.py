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
            _upgrade_sqlite_schema()
            _seed_learning_defaults()
            print("Database initialized.")

    return app


def _seed_learning_defaults():
    from .models import SavedModel, SavedPrompt

    if not SavedModel.query.filter_by(provider_key="openai", name="gpt-4.1-mini").first():
        db.session.add(
            SavedModel(
                provider_key="openai",
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


def _upgrade_sqlite_schema():
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "saved_model" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("saved_model")}
    if "provider_key" not in columns:
        db.session.execute(
            text("ALTER TABLE saved_model ADD COLUMN provider_key VARCHAR(40) NOT NULL DEFAULT 'openai'")
        )
        db.session.commit()

    table_sql = db.session.execute(
        text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'saved_model'")
    ).scalar_one_or_none()
    if table_sql and "UNIQUE (name)" in table_sql:
        db.session.execute(text("PRAGMA foreign_keys=off"))
        db.session.execute(
            text(
                """
                CREATE TABLE saved_model_new (
                    id INTEGER NOT NULL,
                    provider_key VARCHAR(40) NOT NULL DEFAULT 'openai',
                    name VARCHAR(120) NOT NULL,
                    description VARCHAR(255),
                    PRIMARY KEY (id),
                    CONSTRAINT uq_saved_model_provider_name UNIQUE (provider_key, name)
                )
                """
            )
        )
        db.session.execute(
            text(
                """
                INSERT INTO saved_model_new (id, provider_key, name, description)
                SELECT id, provider_key, name, description FROM saved_model
                """
            )
        )
        db.session.execute(text("DROP TABLE saved_model"))
        db.session.execute(text("ALTER TABLE saved_model_new RENAME TO saved_model"))
        db.session.execute(text("PRAGMA foreign_keys=on"))
        db.session.commit()
