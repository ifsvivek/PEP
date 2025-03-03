import subprocess
import tempfile
import os
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from config import Config

groq_llm = ChatGroq(api_key=Config.GROQ_API_KEY, model_name="llama-3.3-70b-versatile")

class CodeExecutor:
    def __init__(self):
        self.supported_languages = {
            'python': {
                'extension': '.py',
                'command': 'python'
            },
            'javascript': {
                'extension': '.js',
                'command': 'node'
            },
            'c': {
                'extension': '.c',
                'command': 'gcc'
            }
        }

    def execute_code(self, code, language, test_cases):
        if language not in self.supported_languages:
            return {'error': 'Language not supported'}

        with tempfile.NamedTemporaryFile(suffix=self.supported_languages[language]['extension'], delete=False) as f:
            f.write(code.encode())
            f.flush()

            try:
                if language == 'c':
                    # Compile C code first
                    output_file = f.name[:-2] + '.exe'
                    subprocess.run([self.supported_languages[language]['command'], f.name, '-o', output_file], 
                                check=True, capture_output=True)
                    results = []
                    for test in test_cases:
                        proc = subprocess.run([output_file], input=test['input'].encode(),
                                           capture_output=True, timeout=5)
                        results.append({
                            'input': test['input'],
                            'expected': test['output'],
                            'actual': proc.stdout.decode().strip()
                        })
                    os.remove(output_file)
                else:
                    # Execute Python or JavaScript
                    results = []
                    for test in test_cases:
                        proc = subprocess.run([self.supported_languages[language]['command'], f.name],
                                           input=test['input'].encode(),
                                           capture_output=True, timeout=5)
                        results.append({
                            'input': test['input'],
                            'expected': test['output'],
                            'actual': proc.stdout.decode().strip()
                        })

                return {
                    'success': True,
                    'results': results,
                    'all_passed': all(r['expected'] == r['actual'] for r in results)
                }

            except subprocess.CalledProcessError as e:
                return {
                    'success': False,
                    'error': e.stderr.decode()
                }
            finally:
                os.unlink(f.name)

    def generate_hint(self, code, problem, language):
        hint_prompt = PromptTemplate(
            input_variables=["code", "problem", "language"],
            template="""
            As a coding mentor, analyze this {language} code and provide a helpful hint for improving it.
            The problem is: {problem}
            
            The current code is:
            {code}
            
            Provide a concise, constructive hint that guides the student towards a better solution without giving away the complete answer.
            Focus on:
            1. Potential logical errors
            2. Performance improvements
            3. Best practices
            4. Common pitfalls
            
            Return only the hint text, keeping it under 100 words.
            """
        )
        
        response = groq_llm(hint_prompt.format(
            code=code,
            problem=problem,
            language=language
        ))
        
        return response.strip()