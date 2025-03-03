import subprocess
import tempfile
import os
import time
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from config import Config
from langchain_core.messages import HumanMessage

groq_llm = ChatGroq(api_key=Config.GROQ_API_KEY, model_name="llama-3.3-70b-versatile")


class CodeExecutor:
    def __init__(self):
        self.supported_languages = {
            "python": {"extension": ".py", "command": "python"},
            "javascript": {"extension": ".js", "command": "node"},
            "c": {"extension": ".c", "command": "gcc"},
        }

    def execute_code(self, code, language, test_cases):
        if language not in self.supported_languages:
            return {"error": "Language not supported"}

        temp_file = None
        output_file = None
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                suffix=self.supported_languages[language]["extension"],
                mode="w+",
                delete=False,
            )

            # Write code to file
            temp_file.write(code)
            temp_file.flush()
            temp_file.close()

            results = []
            if language == "c":
                # Compile C code
                output_file = temp_file.name[:-2] + ".exe"
                compile_process = subprocess.run(
                    [
                        self.supported_languages[language]["command"],
                        temp_file.name,
                        "-o",
                        output_file,
                    ],
                    capture_output=True,
                    check=True,
                )

                # Run tests
                for test in test_cases:
                    proc = subprocess.run(
                        [output_file],
                        input=test["input"].encode(),
                        capture_output=True,
                        timeout=5,
                    )
                    results.append(
                        {
                            "input": test["input"],
                            "expected": test["output"],
                            "actual": proc.stdout.decode().strip(),
                        }
                    )
            else:
                # Execute Python or JavaScript
                for test in test_cases:
                    proc = subprocess.run(
                        [self.supported_languages[language]["command"], temp_file.name],
                        input=test["input"].encode(),
                        capture_output=True,
                        timeout=5,
                    )
                    results.append(
                        {
                            "input": test["input"],
                            "expected": test["output"],
                            "actual": proc.stdout.decode().strip(),
                        }
                    )

            return {
                "success": True,
                "results": results,
                "all_passed": all(r["expected"] == r["actual"] for r in results),
            }

        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr.decode()}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Code execution timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            # Clean up temporary files
            try:
                if temp_file and os.path.exists(temp_file.name):
                    # Add a small delay to ensure file is not in use
                    time.sleep(0.1)
                    os.unlink(temp_file.name)
                if output_file and os.path.exists(output_file):
                    os.unlink(output_file)
            except Exception as e:
                print(f"Warning: Could not delete temporary file: {e}")

    def generate_hint(self, code, problem, language):
        prompt_text = f"""As a coding mentor, analyze this {language} code and provide a helpful hint for improving it.
The problem is: {problem}

The current code is:
{code}

Provide a concise, constructive hint that guides the student towards a better solution without giving away the complete answer.
Focus on:
1. Potential logical errors
2. Performance improvements
3. Best practices
4. Common pitfalls

Return only the hint text, keeping it under 100 words."""

        # Create a proper chat message
        message = HumanMessage(content=prompt_text)

        try:
            # Get response from Groq
            response = groq_llm([message])
            return response.content.strip()
        except Exception as e:
            return f"Sorry, I couldn't generate a hint at the moment. Please try again. Error: {str(e)}"
