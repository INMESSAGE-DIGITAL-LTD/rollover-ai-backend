<?php

namespace App\Http\Controllers\Api\v1;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Http\Controllers\Api\v1\ApiController;
use App\Http\Controllers\Api\v1\SubscriptionController;
use App\Http\Controllers\Api\v1\LiveMatchController;
use App\Http\Controllers\Api\v1\HighlightController;
use Cache;

class HomeController extends Controller
{
    public function home(Request $request)
    {
        $validator = \Validator::make($request->all(), [

            'app_id' => 'required',
            'platform' => 'nullable',
            
        ]);

        if ($validator->fails()) {
            return response()->json(['result' => false, 'message' => $validator->errors()->first()]);
        }

        $user = $request->user();
        if($user){
            $user->email = $user->display_email;
            $user->makeHidden(['id', 'user_type', 'created_at', 'updated_at', 'apps', 'app_id', 'email_verified_at', 'provider', 'status']);
        }

        $apiController = new ApiController();
        $settings = $apiController->settings($request)->getData()->data;

        $subscriptionController = new SubscriptionController();
        $subscriptions = $subscriptionController->subscriptions($request)->getData()->data;

        $liveMatchController = new LiveMatchController();
        $live_matches = $liveMatchController->live_matches($request)->getData()->data;

        $highlightController = new HighlightController();
        $highlights = $highlightController->highlights($request)->getData()->data;

        return response()->json([
            'status' => true,
            'user' => $user,
            'settings' => $settings,
            'subscriptions' => $subscriptions,
            'live_matches' => $live_matches,
            'highlights' => $highlights,
        ]);
    }
}
