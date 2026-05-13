<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| is assigned the "api" middleware group. Enjoy building your API!
|
*/

Route::post('v1/upload-logo', [Controllers\Api\v1\ApiController::class, 'uploadLogo']);

Route::group(['middleware' => ['x_check'], 'prefix' => 'v1'], function ()
{
    
    try {
        date_default_timezone_set(get_option('timezone') ?? 'Asia/Dhaka');
    } catch (Exception $e) {
        //
    }
    
    //Api Controller
    Route::post('settings', [Controllers\Api\v1\ApiController::class, 'settings']);
    Route::post('live_matches', [Controllers\Api\v1\ApiController::class, 'live_matches']);
    Route::post('tips', [Controllers\Api\v1\ApiController::class, 'tips']);
    Route::post('forebet/predictions', [Controllers\Api\v1\ForebetApiController::class, 'predictions']);
    Route::post('forebet/predictions_details', [Controllers\Api\v1\ForebetApiController::class, 'predictions_details']);
    Route::post('highlights', [Controllers\Api\v1\ApiController::class, 'highlights']);
    Route::post('news', [Controllers\Api\v1\ApiController::class, 'news']);
    Route::post('news_details', [Controllers\Api\v1\ApiController::class, 'news_details']);
    Route::post('movie_news', [Controllers\Api\v1\ApiController::class, 'movie_news']);
    Route::post('ringtones', [Controllers\Api\v1\ApiController::class, 'ringtones']);
    Route::post('xgscore', [Controllers\Api\v1\ApiController::class, 'xgscore']);
    Route::post('rapid', [Controllers\Api\v1\ApiController::class, 'rapidApi']);
    Route::post('freefootballtips', [Controllers\Api\v1\ApiController::class, 'freefootballtips']);
    Route::post('freefootballtips_details', [Controllers\Api\v1\ApiController::class, 'freefootballtips_details']);
    
    Route::post('games', [Controllers\Api\v1\PredictionAppApiController::class, 'games']);
    Route::post('today_games', [Controllers\Api\v1\PredictionAppApiController::class, 'today_games']);
    Route::post('free_tips', [Controllers\Api\v1\PredictionAppApiController::class, 'free_tips']);
    Route::post('search', [Controllers\Api\v1\PredictionAppApiController::class, 'search']);
    Route::post('prediction_details', [Controllers\Api\v1\PredictionAppApiController::class, 'prediction_details']);

    //Auth Controller
    Route::post('signup', [Controllers\Api\v1\AuthController::class, 'signup']);
    Route::post('signin', [Controllers\Api\v1\AuthController::class, 'signin']);
    Route::post('signinWithPhone', [Controllers\Api\v1\AuthController::class, 'signinWithPhone']);

    //SubscriptionController
    Route::post('subscriptions', [Controllers\Api\v1\SubscriptionController::class, 'subscriptions']);

    //Auth Controller
    Route::middleware('auth:sanctum')->group( function () {
        Route::post('user', [Controllers\Api\v1\AuthController::class, 'user']);
        Route::post('user_update', [Controllers\Api\v1\AuthController::class, 'user_update']);
        Route::post('upload_profile', [Controllers\Api\v1\AuthController::class, 'upload_profile']);
        Route::post('change_password', [Controllers\Api\v1\AuthController::class, 'change_password']);
        
        Route::post('favorite', [Controllers\Api\v1\ApiController::class, 'favorite']);
        Route::post('favorites', [Controllers\Api\v1\ApiController::class, 'favorites']);

        //SubscriptionController
        Route::post('subscription_update', [Controllers\Api\v1\SubscriptionController::class, 'subscription_update']);
        Route::post('subscription_expired', [Controllers\Api\v1\SubscriptionController::class, 'subscription_expired']);
        Route::post('subscription_restore', [Controllers\Api\v1\SubscriptionController::class, 'subscription_restore']);
        Route::post('payments', [Controllers\Api\v1\SubscriptionController::class, 'payments']);

    });


    
});



Route::group(['middleware' => ['x_check'], 'prefix' => 'xapp'], function () {
    
    try {
        date_default_timezone_set(get_option('timezone') ?? 'Asia/Dhaka');
    } catch (Exception $e) {
        //
    }
    
    Route::group(['middleware' => ['x_check'], 'prefix' => 'v1'], function () {
        //Api Controller
        Route::post('settings', [Controllers\Api\v1\ApiController::class, 'settings']);
        Route::post('live_matches', [Controllers\Api\v1\ApiController::class, 'live_matches']);
        Route::post('tips', [Controllers\Api\v1\ApiController::class, 'tips']);
        Route::post('recent_tips', [Controllers\Api\v1\ApiController::class, 'recent_tips']);
        Route::post('highlights', [Controllers\Api\v1\ApiController::class, 'highlights']);
        Route::post('news', [Controllers\Api\v1\ApiController::class, 'news']);
        Route::post('news_details', [Controllers\Api\v1\ApiController::class, 'news_details']);
        Route::post('movie_news', [Controllers\Api\v1\ApiController::class, 'movie_news']);
        Route::post('ringtones', [Controllers\Api\v1\ApiController::class, 'ringtones']);
        
        Route::post('freefootballtips', [Controllers\Api\v1\ApiController::class, 'freefootballtips']);
        Route::post('freefootballtips_details', [Controllers\Api\v1\ApiController::class, 'freefootballtips_details']);
    
        //Auth Controller
        Route::post('signup', [Controllers\Api\v1\AuthController::class, 'signup']);
        Route::post('signin', [Controllers\Api\v1\AuthController::class, 'signin']);
        Route::post('signinWithPhone', [Controllers\Api\v1\AuthController::class, 'signinWithPhone']);
    
        //SubscriptionController
        Route::post('subscriptions', [Controllers\Api\v1\SubscriptionController::class, 'subscriptions']);
    
        //Auth Controller
        Route::middleware('auth:sanctum')->group( function () {
            Route::post('user', [Controllers\Api\v1\AuthController::class, 'user']);
            Route::post('user_update', [Controllers\Api\v1\AuthController::class, 'user_update']);
            Route::post('upload_profile', [Controllers\Api\v1\AuthController::class, 'upload_profile']);
            Route::post('change_password', [Controllers\Api\v1\AuthController::class, 'change_password']);
            
            Route::post('favorite', [Controllers\Api\v1\ApiController::class, 'favorite']);
            Route::post('favorites', [Controllers\Api\v1\ApiController::class, 'favorites']);
    
            //SubscriptionController
            Route::post('subscription_update', [Controllers\Api\v1\SubscriptionController::class, 'subscription_update']);
            Route::post('subscription_expired', [Controllers\Api\v1\SubscriptionController::class, 'subscription_expired']);
            Route::post('subscription_restore', [Controllers\Api\v1\SubscriptionController::class, 'subscription_restore']);
            Route::post('payments', [Controllers\Api\v1\SubscriptionController::class, 'payments']);
    
        });
    });
});

Route::group(['middleware' => ['x_check'], 'prefix' => 'prediction_app'], function () {
    
    try {
        date_default_timezone_set(get_option('timezone') ?? 'Asia/Dhaka');
    } catch (Exception $e) {
        //
    }
    
    Route::group(['middleware' => ['x_check'], 'prefix' => 'v1'], function () {
        //Api Controller
        Route::post('settings', [Controllers\Api\v1\PredictionAppApiController::class, 'settings']);
        Route::post('highlights', [Controllers\Api\v1\PredictionAppApiController::class, 'highlights']);
        
        Route::post('games', [Controllers\Api\v1\PredictionAppApiController::class, 'games']);
        Route::post('today_games', [Controllers\Api\v1\PredictionAppApiController::class, 'today_games']);
        Route::post('free_tips', [Controllers\Api\v1\PredictionAppApiController::class, 'free_tips']);
        Route::post('search', [Controllers\Api\v1\PredictionAppApiController::class, 'search']);
        
        Route::post('tips', [Controllers\Api\v1\ApiController::class, 'tips']);
        Route::post('another_tips', [Controllers\Api\v1\ApiController::class, 'another_tips']);
        Route::post('freetips', [Controllers\Api\v1\PredictionAppApiController::class, 'free_tips']);
        Route::post('recent_tips', [Controllers\Api\v1\PredictionAppApiController::class, 'recent_tips']);
        Route::post('prediction_details', [Controllers\Api\v1\PredictionAppApiController::class, 'prediction_details']);
        
        
        
        Route::post('news', [Controllers\Api\v1\PredictionAppApiController::class, 'news']);
        Route::post('news_details', [Controllers\Api\v1\PredictionAppApiController::class, 'news_details']);

    
        //Auth Controller
        Route::post('signup', [Controllers\Api\v1\AuthController::class, 'signup']);
        Route::post('signin', [Controllers\Api\v1\AuthController::class, 'signin']);
        Route::post('signinWithPhone', [Controllers\Api\v1\AuthController::class, 'signinWithPhone']);
    
        //SubscriptionController
        Route::post('subscriptions', [Controllers\Api\v1\SubscriptionController::class, 'subscriptions']);
        
        //vote
        Route::post('votes/today_matches', [Controllers\Api\v1\VoteController::class, 'today_matches']);
        Route::post('votes/vote', [Controllers\Api\v1\VoteController::class, 'vote']);
        Route::post('votes/most_votes', [Controllers\Api\v1\VoteController::class, 'most_votes']);
    
        //Auth Controller
        Route::middleware('auth:sanctum')->group( function () {
            Route::post('user', [Controllers\Api\v1\AuthController::class, 'user']);
            Route::post('user_update', [Controllers\Api\v1\AuthController::class, 'user_update']);
            Route::post('upload_profile', [Controllers\Api\v1\AuthController::class, 'upload_profile']);
            Route::post('change_password', [Controllers\Api\v1\AuthController::class, 'change_password']);
            
            Route::post('favorite', [Controllers\Api\v1\ApiController::class, 'favorite']);
            Route::post('favorites', [Controllers\Api\v1\ApiController::class, 'favorites']);
    
            //SubscriptionController
            Route::post('subscription_update', [Controllers\Api\v1\SubscriptionController::class, 'subscription_update']);
            Route::post('subscription_expired', [Controllers\Api\v1\SubscriptionController::class, 'subscription_expired']);
            Route::post('subscription_restore', [Controllers\Api\v1\SubscriptionController::class, 'subscription_restore']);
            Route::post('payments', [Controllers\Api\v1\SubscriptionController::class, 'payments']);
    
        });
    });
});

Route::group(['middleware' => ['x_check'], 'prefix' => 'real_app'], function () {
    
    try {
        date_default_timezone_set(get_option('timezone') ?? 'Asia/Dhaka');
    } catch (Exception $e) {
        //
    }
    
    Route::group(['middleware' => ['x_check'], 'prefix' => 'v1'], function () {
        //Api Controller
        Route::post('settings', [Controllers\Api\v1\RealAppApiController::class, 'settings']);
        Route::post('highlights', [Controllers\Api\v1\RealAppApiController::class, 'highlights']);
        
        Route::post('games', [Controllers\Api\v1\RealAppApiController::class, 'games']);
        Route::post('today_games', [Controllers\Api\v1\RealAppApiController::class, 'today_games']);
        Route::post('free_tips', [Controllers\Api\v1\RealAppApiController::class, 'free_tips']);
        Route::post('search', [Controllers\Api\v1\RealAppApiController::class, 'search']);
        
        Route::post('tips', [Controllers\Api\v1\RealAppApiController::class, 'tips']);
        Route::post('another_tips', [Controllers\Api\v1\ApiController::class, 'another_tips']);
        Route::post('freetips', [Controllers\Api\v1\ApiController::class, 'free_tips']);
        Route::post('recent_tips', [Controllers\Api\v1\RealAppApiController::class, 'recent_tips']);
        Route::post('prediction_details', [Controllers\Api\v1\RealAppApiController::class, 'prediction_details']);
        
        Route::post('freefootballtips', [Controllers\Api\v1\ApiController::class, 'freefootballtips']);
        Route::post('freefootballtips_details', [Controllers\Api\v1\ApiController::class, 'freefootballtips_details']);
        
        
        
        Route::post('news', [Controllers\Api\v1\RealAppApiController::class, 'news']);
        Route::post('news_details', [Controllers\Api\v1\RealAppApiController::class, 'news_details']);

    
        //Auth Controller
        Route::post('signup', [Controllers\Api\v1\AuthController::class, 'signup']);
        Route::post('signin', [Controllers\Api\v1\AuthController::class, 'signin']);
        Route::post('signinWithPhone', [Controllers\Api\v1\AuthController::class, 'signinWithPhone']);
    
        //SubscriptionController
        Route::post('subscriptions', [Controllers\Api\v1\SubscriptionController::class, 'subscriptions']);
        
        //vote
        Route::post('votes/today_matches', [Controllers\Api\v1\VoteController::class, 'today_matches']);
        Route::post('votes/vote', [Controllers\Api\v1\VoteController::class, 'vote']);
        Route::post('votes/most_votes', [Controllers\Api\v1\VoteController::class, 'most_votes']);
    
        //Auth Controller
        Route::middleware('auth:sanctum')->group( function () {
            Route::post('user', [Controllers\Api\v1\AuthController::class, 'user']);
            Route::post('user_update', [Controllers\Api\v1\AuthController::class, 'user_update']);
            Route::post('upload_profile', [Controllers\Api\v1\AuthController::class, 'upload_profile']);
            Route::post('change_password', [Controllers\Api\v1\AuthController::class, 'change_password']);
            
            Route::post('favorite', [Controllers\Api\v1\ApiController::class, 'favorite']);
            Route::post('favorites', [Controllers\Api\v1\ApiController::class, 'favorites']);
    
            //SubscriptionController
            Route::post('subscription_update', [Controllers\Api\v1\SubscriptionController::class, 'subscription_update']);
            Route::post('subscription_expired', [Controllers\Api\v1\SubscriptionController::class, 'subscription_expired']);
            Route::post('subscription_restore', [Controllers\Api\v1\SubscriptionController::class, 'subscription_restore']);
            Route::post('payments', [Controllers\Api\v1\SubscriptionController::class, 'payments']);
    
        });
    });
});