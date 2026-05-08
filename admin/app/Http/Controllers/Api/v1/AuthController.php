<?php

namespace App\Http\Controllers\Api\v1;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Models\User;
use App\Models\AppModel;
use Pion\Laravel\ChunkUpload\Exceptions\UploadMissingFileException;
use Pion\Laravel\ChunkUpload\Handler\AbstractHandler;
use Pion\Laravel\ChunkUpload\Handler\HandlerFactory;
use Pion\Laravel\ChunkUpload\Receiver\FileReceiver;
use Illuminate\Http\UploadedFile;

class AuthController extends Controller
{
    public function signup(Request $request)
    {
        if($request->provider == 'google' || $request->provider == 'apple' || $request->provider == 'facebook'){
            $user = User::where('email', $request->email)->where('user_type', 'user')->exists();
            if($user){
                return $this->signin($request);
            }
        }

        $validator = \Validator::make($request->all(), [

            'first_name' => 'required|string|max:191',
            'last_name' => 'required|string|max:191',
            'email' => 'required|string|email|max:191|unique:users',
            'password' => 'required|string|min:6|confirmed',
            'device_token' => 'required',
            'provider' => 'required',

        ]);

        if ($validator->fails()) {
            return response()->json(['status' => false, 'message' => $validator->errors()->first()]);
        }
        
        $user = new User();

        $user->first_name = $request->first_name;
        $user->last_name = $request->last_name;
        $user->email = $request->email;
        $user->password = \Hash::make($request->password);
        $user->user_type = 'user';
        $user->device_token = $request->device_token;
        $user->provider = $request->provider;
        $user->image = asset('public/default/profile.png');
        $user->status = 1;

        $user->save();

        $tokenResult = $user->createToken($request->device_token)->plainTextToken;
        return response()->json([
            'status' => true,
            'access_token' => $tokenResult,
            'data' => $user,
        ]);
    }

    public function signin(Request $request)
    {
        $validator = \Validator::make($request->all(), [

            'email' => 'required|string|email',
            'password' => 'required|string|min:6',
            'device_token' => 'required',
            'provider' => 'required',
            
        ]);

        if ($validator->fails()) {
            return response()->json(['status' => false, 'message' => $validator->errors()->first()]);
        }

        $user = User::where('email', $request->email)->where('user_type', 'user')->first();
        
        if(!$user || ($user->provider != 'google' && $user->provider != 'apple' && $user->provider != 'facebook')){
            if ((!$user || !\Hash::check($request->password, $user->password)) ) {
                return response()->json([
                    'status' => false,
                    'message' => 'These credentials do not match our records.',
                ]);
            }
        }

        if($request->provider == 'google' || $request->provider == 'apple' || $request->provider == 'facebook'){
            if($request->provider != $user->provider){
                return response()->json([
                    'status' => false,
                    'message' => 'These credentials do not match our recordsd.',
                ]);
            }
        }
        
        $user->tokens()->delete();

        $user->device_token = $request->device_token;

        $user->save();

        $tokenResult = $user->createToken($request->device_token)->plainTextToken;
        return response()->json([
            'status' => true,
            'access_token' => $tokenResult,
            'data' => $user,
        ]);
    }

    public function signinWithPhone(Request $request)
    {
        $validator = \Validator::make($request->all(), [

            'phone' => 'required',
            'uid' => 'required'
            
        ]);

        if ($validator->fails()) {
            return response()->json(['result' => false, 'message' => $validator->errors()->first()]);
        }

        $user = User::where('phone', $request->phone)->first();
        if(!$user){
            $user = new User();

            $user->first_name = 'User';
            $user->last_name = 'User';
            $user->phone = $request->phone;
            $user->password = \Hash::make($request->uid);
            $user->user_type = 'user';
            $user->device_token = $request->device_token;
            $user->provider = 'phone';
            $user->status = 1;

            $user->save();
        }

        $tokenResult = $user->createToken($request->device_token)->plainTextToken;
        return response()->json([
            'status' => true,
            'access_token' => $tokenResult,
            'data' => $user->makeHidden(['id', 'user_type', 'created_at', 'updated_at', 'email_verified_at', 'status']),
        ]);
    }

    public function user(Request $request)
    {
        $user = $request->user();

        return response()->json([
            'status' => true,
            'data' => $user,
        ]);
    }

    public function user_update(Request $request)
    {
        
        $validator = \Validator::make($request->all(), [

            'fields' => 'required:json',

        ]);

        if ($validator->fails()) {
            return response()->json(['status' => false, 'message' => $validator->errors()->first()]);
        }

        $user = $request->user();

        $not_allow_keys = ['phone', 'user_type', 'email'];

        foreach (json_decode($request->fields) as $key => $value) {

            if(in_array($key, $not_allow_keys)){
                return response()->json(['status' => false, 'message' => "The selected $key is invalid."]);
            }
            $user->$key = $value;
        }

        $user->save();
        
        return response()->json([
            'status' => true,
            'user' => $user,
        ]);
    }

    public function upload_profile(Request $request)
    {   
        $validator = \Validator::make($request->all(), [

            'image' => 'required|image',

        ]);

        if ($validator->fails()) {
            return response()->json(['status' => false, 'message' => $validator->errors()->first()]);
        }

        $user = $request->user();

        $receiver = new FileReceiver("image", $request, HandlerFactory::classFromRequest($request));
        if ($receiver->isUploaded() === false) {
            throw new UploadMissingFileException();
        }
        $save = $receiver->receive();
        if ($save->isFinished()) {

            $file = $save->getFile();

            $path = 'public/images/users/';
            $extension = $file->getClientOriginalExtension();
            $fileName =  rand() . time() . "." . $extension;

            $file->move($path, $fileName);

            $user->image = $path . $fileName;

            return response()->json([
                'status' => true,
                'user' => $user,
            ]);
        }
        $handler = $save->handler();
    }

    public function change_password(Request $request)
    {
        $validator = \Validator::make($request->all(), [
            'old_password' => 'required',
            'password' => 'required|string|min:6|confirmed'
        ]);

        if ($validator->fails()) {
            return response()->json(['status' => false, 'message' => $validator->errors()->first()]);
        }

        $user = $request->user();

        if (\Hash::check($request->old_password, $user->password)) {

            if (!\Hash::check($request->password, $user->password)) {

                $user->password = \Hash::make($request->password);
                $user->save();

                return response()->json([
                    'status' => true,
                    'message' => 'Password has been changed!',
                ]);
            } else {

                return response()->json([
                    'status' => false,
                    'message' => 'New Password can not be the old password!',
                ]);
            }
        } else {

            return response()->json([
                'status' => false,
                'message' => 'Old Password not match!',
            ]);
        }
    }
}
