"""
Middleware para monitorear el rendimiento de queries en desarrollo.
"""

import logging
import time
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


class QueryCountDebugMiddleware:
    """Middleware que cuenta queries por request y alerta si son excesivas"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if not settings.DEBUG:
            return self.get_response(request)
        
        connection.queries_log.clear()
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        
        num_queries = len(connection.queries)
        total_time = end_time - start_time
        
        if num_queries > 50:
            logger.warning(
                f"[WARNING] ALERTA: {num_queries} queries en {request.path} "
                f"(tiempo: {total_time:.2f}s)"
            )
            
            sorted_queries = sorted(
                connection.queries,
                key=lambda q: float(q['time']),
                reverse=True
            )[:5]
            
            for i, query in enumerate(sorted_queries, 1):
                logger.warning(
                    f"  {i}. {query['time']}s - {query['sql'][:100]}..."
                )
        
        elif num_queries > 20:
            logger.info(
                f"[INFO] {num_queries} queries en {request.path} "
                f"(tiempo: {total_time:.2f}s)"
            )
        
        response['X-DB-Query-Count'] = str(num_queries)
        response['X-Response-Time'] = f"{total_time:.3f}s"
        
        return response


class CacheHeaderMiddleware:
    """Middleware que agrega headers indicando si la respuesta viene de cache"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        if hasattr(response, 'from_cache') and response.from_cache:
            response['X-Cache-Hit'] = 'true'
        else:
            response['X-Cache-Hit'] = 'false'
        
        return response


class SlowRequestLoggerMiddleware:
    """Middleware que registra requests lentas (> 2 segundos)"""
    
    SLOW_REQUEST_THRESHOLD = 2.0  # segundos
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        
        request_time = end_time - start_time
        
        if request_time > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"[SLOW] REQUEST LENTA: {request.method} {request.path} "
                f"tomó {request_time:.2f}s"
            )
            
            if settings.DEBUG:
                logger.warning(
                    f"   Usuario: {request.user if request.user.is_authenticated else 'Anónimo'}"
                )
                logger.warning(f"   GET params: {dict(request.GET)}")
                logger.warning(f"   Queries: {len(connection.queries)}")
        
        return response
