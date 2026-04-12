<?php

namespace App\Http\Controllers\Api\v1;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Cache;
use App\Models\VoteMatch;
use App\Models\Vote;

class VoteController extends Controller
{
    public function today_matches(Request $request)
    {
        $today = today();
        $client = new \GuzzleHttp\Client();
        $seconds = 60 * 120;
        $matches = Cache::remember("today_matches_$today", $seconds, function () use ($request, $client){
            
            $response = $client->request('GET', 'https://api-football-v1.p.rapidapi.com/v3/fixtures?date=2024-05-05', [
            	'headers' => [
            		'X-RapidAPI-Host' => 'api-football-v1.p.rapidapi.com',
            		'X-RapidAPI-Key' => 'f8d8e1377bmsh6323da85e61df82p1b05e5jsn8b16282c4110',
            	],
            ]);
            
            $matches = json_decode($response->getBody(), true)['response'];
            
            return $matches;
        });
        
        return response()->json(['status' => true, 'data' => $matches]);
    }
    
    public function vote(Request $request)
    {
        
        //return response()->json(['status' => false, 'data' => []]);
        $validator = \Validator::make($request->all(), [
            
            'match_id' => 'required|max:191',
            'link' => 'required',
            'league' => 'required|string|max:191',
            'team_one_name' => 'required|string|max:191',
            'team_one_image' => 'required|max:191',
            'team_two_name' => 'required|string|max:191',
            'team_two_image' => 'required|max:191',
            'vote' => 'required|max:191',
            'datetime' => 'required',
            
        ]);
        
        

        if ($validator->fails()) {
            return response()->json(['result' => false, 'message' => $validator->errors()->first()]);
        }
        
        ini_set('max_execution_time', 0);
        //@set_time_limit(1000);

        $match = VoteMatch::firstOrNew(['link' =>  $request->link]);
        
        $match->match_id = $request->match_id;
        $match->link = $request->link;
        $match->league = $request->league;
        $match->league_image = $request->league_image;
        $match->team_one_name = $request->team_one_name;
        $match->team_one_image = $request->team_one_image;
        $match->team_two_name = $request->team_two_name;
        $match->team_two_image = $request->team_two_image;
        $match->datetime = $request->datetime;
        
        if($request->vote == 'home') {
            $match->home = $match->home + 1;
        }else if($request->vote == 'draw') {
            $match->draw = $match->draw + 1;
        }else if($request->vote == 'away') {
            $match->away = $match->away + 1;
        }
         
        $match->save(); 

        return response()->json(['status' => true, 'data' => $match]);
    }
    
    public function most_votes(Request $request)
    {
        $matches = VoteMatch::select('*', \DB::raw("(home + draw + away) as total"))
                                ->orderBy('total', 'DESC')
                                ->get();

        return response()->json(['status' => true, 'data' => $matches]);
    }
}
