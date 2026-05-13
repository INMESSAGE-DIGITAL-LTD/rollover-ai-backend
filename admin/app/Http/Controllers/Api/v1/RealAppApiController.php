<?php

namespace App\Http\Controllers\Api\v1;

use App\Http\Controllers\Controller;
use App\Models\Setting;
use App\Models\LiveMatch;
use App\Models\Tip;
use App\Models\Highlight;
use Illuminate\Http\Request;
use Cache;
use GuzzleHttp\Client;
use GuzzleHttp\Exception\GuzzleException;
use PHPHtmlParser\Dom;

class RealAppApiController extends Controller
{
    public function settings(Request $request)
    {
        $validator = \Validator::make($request->all(), [

            'platform' => 'required',
            
        ]);

        if ($validator->fails()) {
            return response()->json(['result' => false, 'message' => $validator->errors()->first()]);
        }

        $not_allowed_keys = [

            'site_title',
            'real_app_android_onesignal_app_id',
            'real_app_android_onesignal_api_key',
            'real_app_android_firebase_server_key',
            'real_app_android_firebase_topics',
            'real_app_ios_onesignal_app_id',
            'real_app_ios_onesignal_api_key',
            'real_app_ios_firebase_server_key',
            'real_app_ios_firebase_topics',

        ];
      

        $platform = $request->platform;
        $hidden_platform = ($platform == 'ios' ? 'android' : 'ios');
        
        $settings = Cache::rememberForever("real_app_settings", function () use ($request, $platform, $hidden_platform, $not_allowed_keys){
            $settings = Setting::select("*", \DB::raw("REPLACE(REPLACE(name, '{$platform}_', ''), 'real_app_', '') as name"))
                                ->where("name", "like", "%real_app%")
                                ->where("name", "not like", "%{$hidden_platform}%")
                                ->whereNotIn("name", $not_allowed_keys)
                                ->pluck("value", "name")
                                ->toArray();
            return $settings;
        });

        return response()->json(['status' => true, 'data' => $settings]);
    }
    
    public function today_games(Request $request)
    {
        ini_set('max_execution_time', 0);
        //@set_time_limit(1000);
        
        $seconds = 60 * 60;
        $games = Cache::remember("today_games", $seconds, function () use ($request){
            $games = [];
            for($i = 1; $i <= rand(5, 8); $i++){
                $request->merge(['page' => $i]);
                $games= array_merge($games, self::games($request)->getData()->data);
            }
            return $games;
        });

        return response()->json(['status' => true, 'data' => $games]);
    }
    
    
    public function games(Request $request)
    {
        ini_set('max_execution_time', 0);
        //@set_time_limit(1000);
        
        $page = $request->page ?? 1;
        $date = $request->date ?? 'today';
        $baseUrl = "https://www.rilpredictions.com/fixtures?date=$date&page=$page";
        
        $seconds = 60 * 20;
        $games = Cache::remember("games_{$date}_{$page}", $seconds, function () use ($baseUrl){
            $html = self::loadFromUrl($baseUrl);
            if($html == null){
                return [];
            }
            
            $games = self::getList($html);
            return $games;
        });

        return response()->json(['status' => true, 'data' => $games]);
    }

    public function free_tips(Request $request)
    {
        ini_set('max_execution_time', 0);
        //@set_time_limit(1000);
        
        $page = $request->page ?? 1;
        $date = $request->date ?? 'today';
        $baseUrl = "https://www.rilpredictions.com/quicktips?date=$date&page=$page";
        
        $seconds = 60 * 20;
        $games = Cache::remember("free_tips_{$page}", $seconds, function () use ($baseUrl){
            $html = self::loadFromUrl($baseUrl);
            if($html == null){
                return [];
            }
            
            $games = self::getList($html);
            return $games;
        });

        return response()->json(['status' => true, 'data' => $games]);
    }
    
    public function search(Request $request)
    {
        ini_set('max_execution_time', 0);
        //@set_time_limit(1000);
        
        $q = $request->q;
        $baseUrl = "https://www.rilpredictions.com/search?q=$q";
        
        $seconds = 60 * 20;
        $games = Cache::remember("search_$q", $seconds, function () use ($baseUrl){
            $html = self::loadFromUrl($baseUrl);
            if($html == null){
                return [];
            }
            
            $games = self::getList($html);
            return $games;
        });

        return response()->json(['status' => true, 'data' => $games]);
    }
    
    public function prediction_details(Request $request)
    {
        $validator = \Validator::make($request->all(), [

            'link' => 'required',
            
        ]);

        if ($validator->fails()) {
            return response()->json(['result' => false, 'message' => $validator->errors()->first()]);
        }
        
        ini_set('max_execution_time', 0);
        //@set_time_limit(1000);

        $baseUrl = $request->link;
        
        $seconds = 60 * 60;
        $details = Cache::remember("$baseUrl", $seconds, function () use ($baseUrl){
            $html = self::loadFromUrl($baseUrl);
            if($html == null){
                return [];
            }
            
            $details = self::prediction($html);
            return $details;
        });

        return response()->json(['status' => true, 'data' => $details]);
    }
    
    public function highlights(Request $request)
    {
        $base_url = url('/');
        
        $highlights = Cache::rememberForever("highlights", function (){
            $highlights = Highlight::where('status', 1)
                                ->orderBy('id', 'DESC')
                                ->get();

            return $highlights;
        });

        return response()->json(['status' => true, 'data' => $highlights]);
    }

    public function tips(Request $request)
    {
        $base_url = url('/');
        $page = $request->page ?? 1;
        
        $tips = Cache::rememberForever("tips", function (){
            $tips = Tip::where('status', 1)
                                ->orderBy('match_time', 'DESC')
                                ->get();

            return $tips;
        });

        return response()->json(['status' => true, 'data' => $tips]);
    }

    

    public function recent_tips(Request $request)
    {
        $base_url = url('/');
        $page = $request->page ?? 1;
        $now = \Carbon\Carbon::parse(now())->timestamp;
        
        $seconds = 1 * 60;
        $tips = Cache::remember("recent_tips", $seconds, function () use ($request, $now){
            $tips = Tip::where('status', 1)
                                ->where('match_time', '<', $now)
                                ->orderBy('match_time', 'DESC')
                                ->get();

            return $tips;
        });

        return response()->json(['status' => true, 'data' => $tips]);
    }
    
    // News Api
    public function news(Request $request)
    {
        ini_set('max_execution_time', 0);
        //@set_time_limit(1000);
        
        $page = $request->page ?? 1;
        $baseUrl = "https://www.skysports.com/home/ajax/digrevMoreNewsByBasketId/12040/20/$page/publishDate";
        
        $seconds = 60 * 20;
        $news = Cache::remember("real_app_news_{$page}", $seconds, function () use ($baseUrl){
            $html = self::loadFromUrl($baseUrl);
            if($html == null){
                return [];
            }
            $dom = new Dom;
            $dom->loadStr($html);
            
            $i = 0;
            $news = [];
            foreach ($dom->find('.news-list__item') as $key => $value) {
                $news[$i]['title'] = trim($value->find('.news-list__headline a', 0)->innerText ?? '');
                $news[$i]['description'] = trim($value->find('.news-list__snippet', 0)->text ?? '');
                $news[$i]['author'] = trim($value->find('.label a', 0)->text ?? '');
                $news[$i]['datetime'] = trim($value->find('.label span', 0)->text ?? '');
                $news[$i]['image'] = trim($value->find('img', 0)->getAttribute('data-src', 0) ?? '');
                $news[$i]['link'] = trim($value->find('.news-list__headline a', 0)->getAttribute('href', 0) ?? '');
                
                if(str_contains($news[$i]['link'], '/watch')){
                    continue;
                }
                $i++;
            }
            
            return $news;
        });
        
        return response()->json(['status' => true, 'data' => $news]);
    }
    

    public function news_details(request $request)
    {
        $validator = \Validator::make($request->all(), [

            'link' => 'required',
            
        ]);

        if ($validator->fails()) {
            return response()->json(['result' => false, 'message' => $validator->errors()->first()]);
        }
        
        ini_set('max_execution_time', 0);
        //@set_time_limit(1000);
        
        $link = $request->link;
        $baseUrl = $link;
        
        $seconds = 60 * 20;
        $details = Cache::remember("$baseUrl", $seconds, function () use ($baseUrl){
            $html = self::loadFromUrl($baseUrl);
            if($html == null){
                return [];
            }
            $dom = new Dom;
            $dom->loadStr($html);
            $body = $dom->find('.section-wrap');
            
            $details['title'] = trim($body->find('.sdc-article-header__long-title', 0)->text ?? '');
            $details['subtitle'] = trim($body->find('.sdc-article-header__sub-title', 0)->outerHtml ?? '');
            $details['author'] = trim($body->find('.sdc-article-author__link', 0)->text ?? '');
            $details['datetime'] = trim($body->find('.sdc-article-date__date-time', 0)->text ?? '');
            try{
                $details['image'] = trim($body->find('.sdc-article-image__item')->getAttribute('src', 0) ?? '');
            }catch(\Exception $e){
                $details['image'] = '';
            }
            
            $description = '';
            foreach ($dom->find('.sdc-article-body p, .sdc-article-body h3, .sdc-article-body ui, .sdc-article-body img') as $key => $value) {
                $description .= $value->outerHtml ?? '';
            }
            $details['description'] = $description;
            
            return $details;
        });
        
        return response()->json(['status' => true, 'data' => $details]);
    }
    
    public function getList($html){
        $dom = new Dom;
        $dom->loadStr($html);
        $body = $dom->find('.container');
        
        $games = [];
        $i = 0;
        foreach ($body->find('.card.card-body') as $key => $value) {
            $league_name = $value->find('.fw-light .small', 0)->innerText ?? '';
            if($league_name == ''){
                continue;
            }
            $a = $value->find('a', 0) ?? null;
           
            if(!$a){
                continue;
            }
    
            $time = $a->find('div', 0)->find('.small', 0)->innerText ?? '';
            $result = $a->find('.col-4 .small', 0)->innerText ?? '';
            $league_img = $value->find('.fw-light img', 0);
    
            $team = $a->find('.col .row');
    
            $games[$i]['league_name'] = trim($league_name);
            $games[$i]['league_image'] = $league_img != null ? $league_img->getAttribute('src', 0) : '';
            $games[$i]['time'] = $time;
            $games[$i]['result'] = $result;
            $games[$i]['link'] = 'https://www.rilpredictions.com' . ($a->getAttribute('href', 0) ?? '');
            $games[$i]['team_one_name'] = $team[0]->find('span', 0)->innerText ?? '';
            $games[$i]['team_one_image'] = $team[0]->find('img', 0)->getAttribute('src', 0) ?? '';
            $games[$i]['team_two_name'] = $team[1]->find('span', 0)->innerText ?? '';
            $games[$i]['team_two_image'] = $team[1]->find('img', 0)->getAttribute('src', 0) ?? '';
            $i++;
        }
        
        return $games;
    }
    
    public function prediction($html){
        
        $dom = new Dom;
        $dom->loadStr($html);
        $body = $dom->find('.container');
        
        $list = [];
        // for($i = 0; $i < count($body->find('div.ps-2')); $i++){
        //     $list[] = $i;
        // }
        $tables = $body->find('.card.card-body table');
        
        $predictionDiv = ($tables != null && isset($tables[0])) ? $tables[0] : null;
        $prediction = null;
        if($predictionDiv != null){
            foreach($predictionDiv->find('tbody tr') as $key => $tr){
                $prediction[] = [
                    'title' => trim($tr->find('td', 0)->innerText ?? ''),
                    'value' => trim($tr->find('td', 1)->innerText ?? ''),
                ];
            }
        }
        
        $last5GamesDiv = ($tables != null && isset($tables[1])) ? $tables[1] : null;
        $last5Games = null;
        if($last5GamesDiv != null){
            foreach($last5GamesDiv->find('tbody tr') as $key => $tr){
                $last5Games[] = [
                    'title' => trim($tr->find('td', 1)->innerText ?? ''),
                    'teamOne' => trim($tr->find('td', 0)->innerText ?? ''),
                    'teamTwo' => trim($tr->find('td', 2)->innerText ?? ''),
                ];
            }
        }
        
        $inLeagueComparisonDiv = ($tables != null && isset($tables[2])) ? $tables[2] : null;
        $inLeagueComparison = null;
        if($inLeagueComparisonDiv != null){
            foreach($inLeagueComparisonDiv->find('tbody tr') as $key => $tr){
                $inLeagueComparison[] = [
                    'title' => trim($tr->find('td', 1)->innerText ?? ''),
                    'teamOne' => trim($tr->find('td', 0)->innerText ?? ''),
                    'teamTwo' => trim($tr->find('td', 2)->innerText ?? ''),
                ];
            }
        }
        
        $headToHeadDiv = $body->find('div .card.card-body');
        
        $headToHead = null;
        $i = 0;
        foreach($headToHeadDiv as $key => $data){
            $team = $data->find('.ps-4 .row');
            $headToHead[$i]['league_name'] = trim($data->find('.row span', 0)->text ?? '');
            $headToHead[$i]['team_one_name'] = $team[0]->find('span', 0)->innerText ?? '';
            $headToHead[$i]['team_one_image'] = $team[0]->find('img', 0)->getAttribute('src', 0) ?? '';
            $headToHead[$i]['team_one_goals'] = $team[0]->find('span', 1)->innerText ?? '';
            $headToHead[$i]['team_two_name'] = $team[1]->find('span', 0)->innerText ?? '';
            $headToHead[$i]['team_two_image'] = $team[1]->find('img', 0)->getAttribute('src', 0) ?? '';
            $headToHead[$i]['team_two_goals'] = $team[1]->find('span', 1)->innerText ?? '';
            
            $i++;
        }
        
        $data = [
            'prediction' => $prediction,
            'last5Games' => $last5Games,
            'inLeagueComparison' => $inLeagueComparison,
            'headToHead' => $headToHead,
        ];
        
        return $data;
    }
    
    public function loadFromUrl($url){
        $body = null;
        try {
            $client = new Client();
            $request = $client->request('GET', $url, ['allow_redirects' => false]);
            $body = $request->getBody()->getContents();
        } catch(GuzzleException $e) {
            
        }
        return $body;
    }

}
