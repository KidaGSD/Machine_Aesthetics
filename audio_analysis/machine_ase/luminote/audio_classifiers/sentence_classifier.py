#pip install -U sentence-transformers

from sentence_transformers import SentenceTransformer


class SentenceClassifier:
    def __init__(self, labels: list[str] = None):
        self.model_id = "all-MiniLM-L6-v2"
        self.labels = labels if labels is not None else []
        self.model : SentenceTransformer = None
        self.label_embeddings = None

    def ensure_model(self):
        if self.model is not None:
            return
        self.model = SentenceTransformer(self.model_id)

        self.label_embeddings = self.model.encode(self.labels)

    def encode(self, sentences):
        self.ensure_model()
        return self.model.encode(sentences)

    def similarity(self, embeddings1, embeddings2):
        self.ensure_model()
        return self.model.similarity(embeddings1, embeddings2)
    
    def __call__(self, sentence: str) -> list[tuple[str, float]]:
        self.ensure_model()
        sentence_embedding = self.model.encode([sentence])
        similarity_scores = self.similarity(sentence_embedding, self.label_embeddings)

        # Sort the labels based on similarity scores
        sorted_labels = sorted(zip(self.labels, similarity_scores[0]), key=lambda x: x[1], reverse=True)
        
        # Return the top_n labels with their scores
        return [(label, score) for label, score in sorted_labels]
    
    
#Example usage:
# classifier = SentenceClassifier(labels=["building", "city", "village", "house", "materials", "dog"])
# result = classifier("architect")
# print("Top labels and their similarity scores:")
# for label, score in result:
#     print(f"{label}: {score:.4f}")

