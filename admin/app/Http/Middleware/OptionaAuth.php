<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class OptionaAuth
{
    /**
     * Handle an incoming request.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Closure(\Illuminate\Http\Request): (\Illuminate\Http\Response|\Illuminate\Http\RedirectResponse)  $next
     * @return \Illuminate\Http\Response|\Illuminate\Http\RedirectResponse
     */
    public function handle(Request $request, Closure $next)
    {
        if ($request->bearerToken()) {
            $user = \Auth::guard('sanctum')->user();
            if($user){
                \Auth::setUser($user);
            }
        }
        return $next($request);
    }
}
