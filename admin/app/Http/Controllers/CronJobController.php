<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Cache;
use Carbon\Carbon;
use App\Models\Notification;

class CronJobController extends Controller
{
    public function prediction_notification(Request $request)
    {
        $all_matches = self::today_matches($request);
        $upcoming_matches = [];
        
        foreach($all_matches AS $key => $match){
            $matchUtc = Carbon::createFromTimestamp($match['fixture']['timestamp']);
            if($match['fixture']['status']['short'] == 'NS'){
                $upcoming_matches[] = $match;
            }
        }
        
        $match = $upcoming_matches[array_rand($upcoming_matches)];
        $prediction = self::get_prediction($match['fixture']['id']);
        
        $title = '⚽ ' . $match['league']['name'] . ' - ' . $match['teams']['home']['name'] . ' vs ' . $match['teams']['away']['name'];
    
        $message = '🎯 ' . 'Prediction - ' . $prediction['winner']['name'] . ': ' . ($prediction['winner']['comment'] ?? 'Win');
       
        
        $notification = new Notification();

        $notification->title = $title;
        $notification->message = $message;
        $notification->app = 'football_app';

        $additional_data = [
            'action_url' => $notification->action_url,
        ];
    

        send_notification($notification, $additional_data);
        
        //$notification->app = 'prediction_app';
        
        //prediction_app_send_notification($notification, $additional_data);
        
        return true;
    }
    
    public function get_prediction($id)
    {
        $client = new \GuzzleHttp\Client();

        $response = $client->request('GET', "https://api-football-v1.p.rapidapi.com/v3/predictions?fixture=$id", [
        	'headers' => [
        		'X-RapidAPI-Host' => 'api-football-v1.p.rapidapi.com',
            		'X-RapidAPI-Key' => 'f8d8e1377bmsh6323da85e61df82p1b05e5jsn8b16282c4110',
        	],
        ]);
        
        $prediction = json_decode($response->getBody(), true)['response'][0]['predictions'];
        
        return $prediction;
    }
    
    public function today_matches(Request $request)
    {
        $today = today();
        $client = new \GuzzleHttp\Client();
        $seconds = 60 * 60;
        $matches = Cache::remember("xtoday_matches_$today", $seconds, function () use ($request, $client){
            
            $response = $client->request('GET', 'https://api-football-v1.p.rapidapi.com/v3/fixtures?date=2024-05-05', [
            	'headers' => [
            		'X-RapidAPI-Host' => 'api-football-v1.p.rapidapi.com',
            		'X-RapidAPI-Key' => 'f8d8e1377bmsh6323da85e61df82p1b05e5jsn8b16282c4110',
            	],
            ]);
            
            $matches = json_decode($response->getBody(), true)['response'];
            
            return $matches;
        });
        
        return $matches;
    }
}
