from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from config import Config

groq_llm = ChatGroq(api_key=Config.GROQ_API_KEY, model_name="llama-3.3-70b-versatile")

class QuestionGenerator:
    def __init__(self):
        self.prompt_template = PromptTemplate(
            input_variables=["language", "difficulty"],
            template="""Generate a simple coding question for {language} programming at {difficulty} level.
            Return the response in the following JSON format:
            {
                "title": "Question title",
                "description": "Detailed problem description",
                "example": "Input/Output example",
                "template": "Starter code template",
                "test_cases": [
                    {{"input": "test input 1", "output": "expected output 1"}},
                    {{"input": "test input 2", "output": "expected output 2"}},
                    {{"input": "test input 3", "output": "expected output 3"}}
                ]
            }
            
            For {difficulty} level, focus on:
            - Basic syntax and operations
            - Simple input/output
            - Basic data types
            - Simple mathematical operations
            - String manipulation basics
            
            Ensure the test cases are simple and straightforward."""
        )

    def generate_question(self, language):
        try:
            prompt = self.prompt_template.format(language=language, difficulty="beginner")
            response = groq_llm.invoke(prompt)
            return eval(response.content)  # Convert string response to dict
        except Exception as e:
            # Fallback question if generation fails
            return self.get_fallback_question(language)

    def get_fallback_question(self, language):
        templates = {
            'python': {
                'title': 'Sum Two Numbers',
                'description': 'Write a function that takes two numbers as input and returns their sum.',
                'example': 'Input: 5 3\nOutput: 8',
                'template': 'def sum_numbers(a, b):\n    # Your code here\n    pass\n\n# Read input\na, b = map(int, input().split())\nresult = sum_numbers(a, b)\nprint(result)',
                'test_cases': [
                    {'input': '5 3', 'output': '8'},
                    {'input': '10 20', 'output': '30'},
                    {'input': '0 0', 'output': '0'}
                ]
            },
            'javascript': {
                'title': 'Reverse String',
                'description': 'Write a function that reverses a string.',
                'example': 'Input: hello\nOutput: olleh',
                'template': 'function reverseString(str) {\n    // Your code here\n}\n\nconst input = require("readline")\n    .createInterface({\n        input: process.stdin,\n        output: process.stdout\n    });\n\ninput.on("line", (line) => {\n    console.log(reverseString(line));\n    input.close();\n});',
                'test_cases': [
                    {'input': 'hello', 'output': 'olleh'},
                    {'input': 'world', 'output': 'dlrow'},
                    {'input': 'code', 'output': 'edoc'}
                ]
            },
            'c': {
                'title': 'Calculate Square',
                'description': 'Write a program that calculates the square of a number.',
                'example': 'Input: 5\nOutput: 25',
                'template': '#include <stdio.h>\n\nint square(int n) {\n    // Your code here\n    return 0;\n}\n\nint main() {\n    int n;\n    scanf("%d", &n);\n    printf("%d\\n", square(n));\n    return 0;\n}',
                'test_cases': [
                    {'input': '5', 'output': '25'},
                    {'input': '3', 'output': '9'},
                    {'input': '0', 'output': '0'}
                ]
            }
        }
        return templates.get(language, templates['python'])