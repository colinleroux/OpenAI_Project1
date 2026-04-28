from .extensions import db
from datetime import datetime, timezone


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)


class SavedPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    prompt_text = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<SavedPrompt {self.title!r}>"


class SavedRequestText(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider_key = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    request_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SavedRequestText {self.provider_key!r}:{self.title!r}>"


class SavedModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider_key = db.Column(db.String(40), nullable=False, default="openai")
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("provider_key", "name", name="uq_saved_model_provider_name"),
    )

    def __repr__(self):
        return f"<SavedModel {self.provider_key!r}:{self.name!r}>"


class ProviderConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider_key = db.Column(db.String(40), unique=True, nullable=False)
    default_model_id = db.Column(db.Integer, db.ForeignKey("saved_model.id"), nullable=True)
    temperature = db.Column(db.Float, nullable=False, default=1.0)
    max_output_tokens = db.Column(db.Integer, nullable=True)

    default_model = db.relationship("SavedModel")

    def __repr__(self):
        return f"<ProviderConfig {self.provider_key!r}>"


class RequestLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider_key = db.Column(db.String(40), nullable=False)
    model_name = db.Column(db.String(120), nullable=False)
    prompt_id = db.Column(db.Integer, db.ForeignKey("saved_prompt.id"), nullable=True)
    prompt_title = db.Column(db.String(120), nullable=True)
    request_text = db.Column(db.Text, nullable=False)
    included_files = db.Column(db.Boolean, nullable=False, default=False)
    attachment_names = db.Column(db.Text, nullable=True)
    estimated_input_tokens = db.Column(db.Integer, nullable=True)
    actual_input_tokens = db.Column(db.Integer, nullable=True)
    actual_output_tokens = db.Column(db.Integer, nullable=True)
    actual_total_tokens = db.Column(db.Integer, nullable=True)
    cached_tokens = db.Column(db.Integer, nullable=True)
    reasoning_tokens = db.Column(db.Integer, nullable=True)
    response_id = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="measured")
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    prompt = db.relationship("SavedPrompt")
