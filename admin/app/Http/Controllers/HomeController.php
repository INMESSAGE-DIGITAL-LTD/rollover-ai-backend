<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class HomeController extends Controller
{
    /**
     * Show the application dashboard.
     *
     * @return \Illuminate\Contracts\Support\Renderable
     */
    public function privacy_policy(Request $request)
    {
        return view('privacy_policy');
    }
    
    /**
     * Show the application dashboard.
     *
     * @return \Illuminate\Contracts\Support\Renderable
     */
    public function terms_conditions(Request $request)
    {
        return view('terms_conditions');
    }
    
    /**
     * Show the application dashboard.
     *
     * @return \Illuminate\Contracts\Support\Renderable
     */
    public function real_prediction_privacy_policy(Request $request)
    {
        return view('real_prediction_privacy_policy');
    }
    
    /**
     * Show the application dashboard.
     *
     * @return \Illuminate\Contracts\Support\Renderable
     */
    public function real_prediction_terms_conditions(Request $request)
    {
        return view('real_prediction_terms_conditions');
    }
    
    /**
     * Show the application dashboard.
     *
     * @return \Illuminate\Contracts\Support\Renderable
     */
    public function real_privacy_policy(Request $request)
    {
        return view('real_privacy_policy');
    }
    
    /**
     * Show the application dashboard.
     *
     * @return \Illuminate\Contracts\Support\Renderable
     */
    public function real_terms_conditions(Request $request)
    {
        return view('real_terms_conditions');
    }
    
    
    
    
    
    
    
    
}
