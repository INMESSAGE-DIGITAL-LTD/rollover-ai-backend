<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Redirect;
use App\Http\Controllers\Controller;
use App\Utils\Installer;
use Validator;
use Hash;

class InstallController extends Controller
{	
	public function __construct()
    {	
    	define('STDIN',fopen("php://stdin","r"));
		if(env('APP_INSTALLED', false) == true){
			Redirect::to('/')->send();
		}
    }
	
    public function index()
    {
		$requirements = Installer::checkServerRequirements();
        return view('install.step_1',compact('requirements'));
    }
	
	public function database(Request $request)
    {
    	if($request->isMethod('get')){
        	return view('install.step_2');
        }else{
			if(Installer::createDbTables($request->hostname, $request->database, $request->username, $request->password) == false){
	           return redirect()->back()->with("error","Invalid Database Settings !");
			}
			
			return redirect('installation/step/two');
        }
    }
	
	public function user(Request $request)
    {
    	if($request->isMethod('get')){
        	return view('install.step_3');
        }else{
        	$validator = Validator::make($request->all(), [	

	            'first_name' => 'required|string|max:191',
	            'last_name' => 'required|string|max:191',
	            'email' => 'required|string|email|max:191|unique:users',
	            'password' => 'required|string|min:6',

	        ]);
			
			if ($validator->fails()) {	
					return redirect()->back()
								->withErrors($validator)
								->withInput();			
			}
			
			$password = Hash::make($request->password);
			
			Installer::createUser($request->first_name, $request->last_name, $request->email, $password);
	        
			return redirect('installation/step/three');
        }
	}

	public function settings(Request $request)
    {
        if($request->isMethod('get')){
        	return view('install.step_4');
        }else{
        	Installer::updateSettings($request->all());
	        Installer::finalTouches();
	        \Artisan::call('config:clear');
	        \Artisan::call('cache:clear');
	        \Artisan::call('key:generate');
			return redirect('general_settings');
        }
    }
}
