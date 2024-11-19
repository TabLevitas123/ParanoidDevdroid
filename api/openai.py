
class Completion:
    @staticmethod
    def create(engine, prompt, max_tokens):
        return {'choices': [{'text': f'Mock response for prompt: {prompt}'}]}
