from .extensions import db


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


class SavedModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<SavedModel {self.name!r}>"


class ProviderConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider_key = db.Column(db.String(40), unique=True, nullable=False)
    default_model_id = db.Column(db.Integer, db.ForeignKey("saved_model.id"), nullable=True)
    temperature = db.Column(db.Float, nullable=False, default=1.0)
    max_output_tokens = db.Column(db.Integer, nullable=True)

    default_model = db.relationship("SavedModel")

    def __repr__(self):
        return f"<ProviderConfig {self.provider_key!r}>"
