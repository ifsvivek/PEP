import os
import json
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config import Config
import re
import time

# Initialize Groq LLM with improved parameters
groq_llm = ChatGroq(
    api_key=Config.GROQ_API_KEY, 
    model_name="llama-3.3-70b-versatile",
    temperature=0.7,  # Slightly increased for more creative content
    top_p=0.9,        # Maintain coherence while allowing some creativity
    max_tokens=32000   # Ensure we get comprehensive responses
)

def clean_json_string(json_str):
    """Clean and extract valid JSON from a string"""
    # Find JSON content between curly braces if not already proper JSON
    if not json_str.strip().startswith("{"):
        start = json_str.find("{")
        if start != -1:
            json_str = json_str[start:]
    if not json_str.strip().endswith("}"):
        end = json_str.rfind("}")
        if end != -1:
            json_str = json_str[:end + 1]
    
    # Handle any trailing commas in arrays or objects (common JSON error)
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    return json_str.strip()

def generate_content(topic):
    """Generate rich educational content for a given topic with interactive elements"""

    content_prompt = PromptTemplate(
        input_variables=["topic"],
        template="""
        You are an expert educational content creator specializing in creating engaging, accurate, and comprehensive content. 
        Create detailed, pedagogically sound educational content about {topic}.
        
        Your response MUST be formatted as valid JSON with the following structure:
        {{
            "title": "{topic}",
            "introduction": "A comprehensive introductory paragraph explaining what {topic} is, its significance, and why it matters (minimum 200 words)",
            "learning_objectives": [
                "After studying this content, you will be able to...",
                "At least 3-5 specific learning objectives"
            ],
            "sections": [
                {{
                    "heading": "Key Concept 1",
                    "content": "Detailed explanation with clear descriptions and real-world connections (minimum 250 words)",
                    "examples": ["Specific Example 1 with details", "Specific Example 2 with details"],
                    "interactive_element": {{
                        "type": "reflection_question",
                        "content": "A thought-provoking question that helps solidify understanding"
                    }}
                }},
                {{
                    "heading": "Key Concept 2", 
                    "content": "Detailed explanation with clear descriptions and real-world connections (minimum 250 words)",
                    "examples": ["Specific Example 1 with details", "Specific Example 2 with details"],
                    "interactive_element": {{
                        "type": "case_study",
                        "content": "A brief real-world application or scenario that illustrates this concept"
                    }}
                }},
                {{
                    "heading": "Key Concept 3",
                    "content": "Detailed explanation with clear descriptions and real-world connections (minimum 250 words)",
                    "examples": ["Specific Example 1 with details", "Specific Example 2 with details"],
                    "interactive_element": {{
                        "type": "practical_activity",
                        "content": "A hands-on activity that demonstrates this concept"
                    }}
                }},
                {{
                    "heading": "Applications and Importance",
                    "content": "Explanation of real-world applications and why this knowledge matters (minimum 200 words)",
                    "examples": ["Industry application", "Research application", "Everyday life application"],
                    "interactive_element": {{
                        "type": "discussion_prompt",
                        "content": "A thought-provoking question about applying this knowledge"
                    }}
                }}
            ],
            "key_terms": [
                {{
                    "term": "Important Term 1",
                    "definition": "Clear, concise definition"
                }},
                {{
                    "term": "Important Term 2",
                    "definition": "Clear, concise definition"
                }},
                {{
                    "term": "Important Term 3",
                    "definition": "Clear, concise definition"
                }}
            ],
            "summary": "A comprehensive summary tying together the main concepts covered (minimum 200 words)",
            "further_reading": [
                {{
                    "title": "Resource Title 1",
                    "author": "Author Name(s)",
                    "description": "Brief description of what this resource covers"
                }},
                {{
                    "title": "Resource Title 2",
                    "author": "Author Name(s)",
                    "description": "Brief description of what this resource covers"
                }},
                {{
                    "title": "Resource Title 3",
                    "author": "Author Name(s)",
                    "description": "Brief description of what this resource covers"
                }}
            ]
        }}
        
        Ensure all content is:
        1. Factually accurate and up-to-date
        2. Educationally sound with clear explanations
        3. Engaging with real-world connections
        4. Appropriate for advanced high school or college-level learners
        5. Free of jargon unless the jargon is explained
        
        Use specific examples, analogies, and clear explanations to make complex concepts accessible.
        Your response must be ONLY the JSON with no additional text or explanations.
        """,
    )

    content_chain = LLMChain(llm=groq_llm, prompt=content_prompt)

    # Add retry mechanism for reliability
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            response = content_chain.run(topic=topic)
            json_str = clean_json_string(response)
            content = json.loads(json_str)
            
            # Validation - ensure we have the minimum expected structure
            if (
                "title" in content and 
                "introduction" in content and 
                "sections" in content and 
                len(content["sections"]) >= 2
            ):
                return content
            else:
                print(f"Attempt {attempt+1}: Content validation failed. Retrying...")
        except json.JSONDecodeError as e:
            print(f"Attempt {attempt+1}: JSON parsing error - {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        except Exception as e:
            print(f"Attempt {attempt+1}: Error generating content - {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    # If all attempts fail, return enhanced fallback content
    return create_fallback_content(topic)

def create_fallback_content(topic):
    """Create more detailed fallback content when AI generation fails"""
    return {
        "title": topic,
        "introduction": f"Welcome to this introduction to {topic}. This field is significant because it helps us understand key aspects of our world and has applications across many domains of human knowledge. By studying {topic}, you will develop insights that can be applied to solve real-world problems and advance our collective understanding.",
        "learning_objectives": [
            f"Understand the fundamental concepts of {topic}",
            f"Recognize the historical development of {topic}",
            f"Apply basic principles of {topic} to simple problems",
            f"Connect {topic} to related fields of study"
        ],
        "sections": [
            {
                "heading": f"Fundamentals of {topic}",
                "content": f"To understand {topic}, we must first explore its fundamental principles. These building blocks form the foundation upon which more complex ideas are constructed. The conceptual framework of {topic} has evolved over time through the work of many scholars and practitioners who have contributed to its development. By mastering these foundational elements, you'll be better equipped to understand advanced applications.",
                "examples": [
                    f"Basic example of {topic} applied to a simple scenario",
                    f"Historical context showing the evolution of {topic}"
                ],
                "interactive_element": {
                    "type": "reflection_question",
                    "content": f"How might understanding {topic} change your perspective on related areas?"
                }
            },
            {
                "heading": "Key Principles",
                "content": f"Several key principles define how {topic} works in practice. These principles represent patterns that experts have identified through careful observation and analysis. Understanding these principles will help you recognize similar patterns in different contexts and develop a deeper appreciation for the subject's nuances.",
                "examples": [
                    "Principle 1 with concrete illustration",
                    "Principle 2 demonstrated in context"
                ],
                "interactive_element": {
                    "type": "practical_activity",
                    "content": f"Try applying one principle of {topic} to a familiar situation and observe the results."
                }
            },
            {
                "heading": "Applications",
                "content": f"{topic} has numerous practical applications that demonstrate its value. From theoretical implementations to everyday uses, the concepts you're learning have real-world relevance. By connecting theory to practice, you'll develop a more holistic understanding of the subject.",
                "examples": [
                    "Application in academic research",
                    "Application in industry",
                    "Application in everyday life"
                ],
                "interactive_element": {
                    "type": "case_study",
                    "content": f"Consider how {topic} has been applied to solve a recent challenge in its field."
                }
            }
        ],
        "key_terms": [
            {
                "term": f"{topic} Framework",
                "definition": f"The foundational structure that organizes the principles of {topic}"
            },
            {
                "term": "Core Concepts",
                "definition": "The essential ideas that must be understood to master this subject"
            },
            {
                "term": "Application Domain",
                "definition": "The areas where this knowledge can be practically applied"
            }
        ],
        "summary": f"This module has introduced you to {topic}, covering its fundamental concepts, key principles, and practical applications. By understanding these elements, you've taken an important first step in mastering this subject. Remember that {topic} connects to many other areas of study and has valuable real-world applications. Continue exploring these connections to deepen your knowledge.",
        "further_reading": [
            {
                "title": f"Introduction to {topic}",
                "author": "Academic Press",
                "description": "A comprehensive beginner's guide to the subject"
            },
            {
                "title": f"Advanced {topic}: Theory and Practice",
                "author": "University Publishing",
                "description": "In-depth exploration of advanced concepts"
            },
            {
                "title": f"{topic} in the Modern World",
                "author": "Contemporary Scholars",
                "description": "How this subject applies to current challenges"
            }
        ]
    }

def generate_quiz(content):
    """Generate quiz questions based on the content with enhanced variety and quality"""

    quiz_prompt = PromptTemplate(
        input_variables=["content"],
        template="""
        As an expert educator, create a comprehensive assessment based on this educational content. Develop 5 multiple-choice questions that test different cognitive levels (knowledge, understanding, application, analysis).

        CONTENT:
        {content}
        
        Your response MUST be a valid JSON object with this exact structure:
        {{
            "topic": "Topic Name",
            "instructions": "Brief instructions for the quiz taker",
            "questions": [
                {{
                    "question": "A clear, specific question?",
                    "question_type": "knowledge|understanding|application|analysis",
                    "options": [
                        "A specific, plausible answer choice",
                        "Another specific, plausible answer choice",
                        "Another specific, plausible answer choice",
                        "Another specific, plausible answer choice"
                    ],
                    "correct": "The exact text of the correct answer from options",
                    "explanation": "Brief explanation of why the answer is correct"
                }}
            ]
        }}

        Ensure your questions:
        1. Are balanced across different sections of the content
        2. Test different cognitive levels
        3. Use clear, unambiguous language
        4. Have plausible distractors (wrong answers)
        5. Include at least one application or analysis question
        
        Return ONLY the JSON with no additional text.
        """,
    )

    quiz_chain = LLMChain(llm=groq_llm, prompt=quiz_prompt)

    # Add retry mechanism for reliability
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            response = quiz_chain.run(content=json.dumps(content))
            json_str = clean_json_string(response)
            quiz_data = json.loads(json_str)
            
            # Validate quiz data
            if (
                "questions" in quiz_data and 
                isinstance(quiz_data["questions"], list) and 
                len(quiz_data["questions"]) > 0
            ):
                return quiz_data
            else:
                print(f"Attempt {attempt+1}: Quiz validation failed. Retrying...")
        except json.JSONDecodeError as e:
            print(f"Attempt {attempt+1}: Quiz JSON parsing error - {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        except Exception as e:
            print(f"Attempt {attempt+1}: Error generating quiz - {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    # Return fallback quiz if all attempts fail
    return create_fallback_quiz(content)

def create_fallback_quiz(content):
    """Create a basic quiz when AI generation fails"""
    topic = content.get("title", "Topic")
    
    # Extract some content pieces to make the fallback less generic
    sections = content.get("sections", [])
    section_headings = [s.get("heading", f"Section {i+1}") for i, s in enumerate(sections)]
    
    return {
        "topic": topic,
        "instructions": f"Answer these questions about {topic} to test your understanding.",
        "questions": [
            {
                "question": f"What is {topic} primarily concerned with?",
                "question_type": "understanding",
                "options": [
                    content.get("introduction", "").split(".")[0] if content.get("introduction") else f"Understanding the foundations of {topic}",
                    f"Exploring mathematics only",
                    f"Historical figures in {topic}",
                    f"The geography of {topic}"
                ],
                "correct": content.get("introduction", "").split(".")[0] if content.get("introduction") else f"Understanding the foundations of {topic}",
                "explanation": "This is the primary focus as described in the introduction."
            },
            {
                "question": f"Which of the following is a key concept in {topic}?" if section_headings else f"What is an important aspect of {topic}?",
                "question_type": "knowledge",
                "options": [
                    section_headings[0] if section_headings else f"Core principles",
                    "Unrelated concept A",
                    "Unrelated concept B",
                    "Unrelated concept C"
                ],
                "correct": section_headings[0] if section_headings else f"Core principles",
                "explanation": "This is one of the main concepts covered in the content."
            },
            {
                "question": f"How might you apply {topic} in a real-world scenario?",
                "question_type": "application",
                "options": [
                    f"Through analysis of related systems",
                    f"By ignoring its principles",
                    f"Only in theoretical contexts",
                    f"It has no practical applications"
                ],
                "correct": f"Through analysis of related systems",
                "explanation": f"The content explains how {topic} can be applied to understand and work with practical scenarios."
            }
        ]
    }
