"""
Servicio para interactuar con la API de Gemini (o Claude)
"""
import os
import json
from typing import List, Dict, Optional
import google.generativeai as genai
from config import Config

class GeminiService:
    """Cliente para la API de Gemini"""
    
    def __init__(self):
        """Inicializa el cliente de Gemini"""
        Config.validar_configuracion()
        
        genai.configure(api_key=Config.GEMINI_API_KEY)
        
        # Configuración del modelo
        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 2048,
        }
        
        self.safety_settings = [
            {
                'category': 'HARM_CATEGORY_HARASSMENT',
                'threshold': 'BLOCK_MEDIUM_AND_ABOVE'
            },
            {
                'category': 'HARM_CATEGORY_HATE_SPEECH',
                'threshold': 'BLOCK_MEDIUM_AND_ABOVE'
            },
            {
                'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
                'threshold': 'BLOCK_MEDIUM_AND_ABOVE'
            },
            {
                'category': 'HARM_CATEGORY_DANGEROUS_CONTENT',
                'threshold': 'BLOCK_MEDIUM_AND_ABOVE'
            }
        ]
        
        self.model = genai.GenerativeModel(
            model_name=Config.GEMINI_MODEL,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )
    
    def generar_respuesta(self, mensajes: List[Dict]) -> str:
        """
        Genera una respuesta usando Gemini
        
        Args:
            mensajes: Lista de mensajes con formato [{'role': 'user'|'system', 'content': '...'}]
        
        Returns:
            Respuesta generada por el modelo
        """
        try:
            # Convertir formato de mensajes a formato Gemini
            prompt_completo = self._convertir_mensajes_a_prompt(mensajes)
            
            # Generar respuesta
            response = self.model.generate_content(prompt_completo)
            
            return response.text
        
        except Exception as e:
            print(f"Error al generar respuesta: {str(e)}")
            return self._generar_respuesta_fallback()
    
    def generar_respuesta_streaming(self, mensajes: List[Dict]):
        """
        Genera respuesta en modo streaming para respuestas en tiempo real
        
        Args:
            mensajes: Lista de mensajes
        
        Yields:
            Chunks de texto de la respuesta
        """
        try:
            prompt_completo = self._convertir_mensajes_a_prompt(mensajes)
            
            response = self.model.generate_content(
                prompt_completo,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        
        except Exception as e:
            print(f"Error en streaming: {str(e)}")
            yield self._generar_respuesta_fallback()
    
    def _convertir_mensajes_a_prompt(self, mensajes: List[Dict]) -> str:
        """
        Convierte lista de mensajes al formato de prompt de Gemini
        
        Args:
            mensajes: Lista de mensajes
        
        Returns:
            Prompt formateado
        """
        prompt_parts = []
        
        for mensaje in mensajes:
            role = mensaje.get('role', 'user')
            content = mensaje.get('content', '')
            
            if role == 'system':
                prompt_parts.append(f"INSTRUCCIONES DEL SISTEMA:\n{content}\n")
            elif role == 'user':
                prompt_parts.append(f"Usuario: {content}\n")
            elif role == 'assistant':
                prompt_parts.append(f"Asistente: {content}\n")
        
        return "\n".join(prompt_parts)
    
    def _generar_respuesta_fallback(self) -> str:
        """Genera una respuesta por defecto en caso de error"""
        return (
            "Lo siento, estoy experimentando dificultades técnicas en este momento. "
            "Por favor, intenta nuevamente en unos momentos o reformula tu pregunta."
        )
    
    def get_modelo_actual(self) -> str:
        """Retorna el nombre del modelo actual"""
        return Config.GEMINI_MODEL
    
    def cambiar_temperatura(self, temperatura: float):
        """
        Cambia la temperatura del modelo
        
        Args:
            temperatura: Valor entre 0 y 1
        """
        if 0 <= temperatura <= 1:
            self.generation_config['temperature'] = temperatura
            # Recrear el modelo con nueva configuración
            self.model = genai.GenerativeModel(
                model_name=Config.GEMINI_MODEL,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )