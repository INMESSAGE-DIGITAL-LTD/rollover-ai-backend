<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Auth\AuthenticationException;

class XCheck
{
    /**
     * Handle an incoming request.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Closure  $next
     * @return mixed
     */
    public function handle($request, Closure $next)
    {
        $x_api_key = $request->header('X-API-KEY');

        if ($x_api_key == '') {
            return response()->json(['status' => false, 'message' => 'Your API key is missing.']);
        } else {
            
            if (!in_array($x_api_key, [ENV('X_API_KEY'), ENV('X_API_KEY2')])) {
                return response()->json(['status' => false, 'message' => 'Your API key is invalid or incorrect.']);
            }
            
            return $next($request);
        }
    }
}
