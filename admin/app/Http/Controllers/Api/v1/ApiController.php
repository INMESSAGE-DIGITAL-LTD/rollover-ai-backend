<?php

namespace App\Http\Controllers\Api\v1;

use App\Http\Controllers\Controller;
use App\Models\Setting;
use App\Models\LiveMatch;
use App\Models\Tip;
use App\Models\FreeTip;
use App\Models\AnotherTip;
use App\Models\Highlight;
use Illuminate\Http\Request;
use Cache;
use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;
use PHPHtmlParser\Dom;
// use Carbon\Carbon;
use Carbon\Carbon;


class ApiController extends Controller
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
            'android_onesignal_app_id',
            'android_onesignal_api_key',
            'android_firebase_server_key',
            'android_firebase_topics',
            'ios_onesignal_app_id',
            'ios_onesignal_api_key',
            'ios_firebase_server_key',
            'ios_firebase_topics',

        ];

        $platform = $request->platform;
        $hidden_platform = ($platform == 'ios' ? 'android' : 'ios');
        
        $settings = Cache::rememberForever("settings", function () use ($request, $platform, $hidden_platform, $not_allowed_keys){
            $settings = Setting::select("*", \DB::raw("REPLACE(name, '{$platform}_', '') as name"))
                                ->where("name", "not like", "%{$hidden_platform}%")
                                ->whereNotIn("name", $not_allowed_keys)
                                ->pluck("value", "name")
                                ->toArray();
            return $settings;
        });

        return response()->json(['status' => true, 'data' => $settings]);
    }

    public function live_matches(Request $request)
    {
        $base_url = url('/');
        $page = $request->page ?? 1;
        
        $live_matches = Cache::rememberForever("live_matches", function () use ($request, $base_url){
            $live_matches = LiveMatch::with(['streamingSources'])
                                ->where('status', 1)
                                ->orderBy('match_time', 'ASC')
                                ->get();

            return $live_matches;
        });

        return response()->json(['status' => true, 'data' => $live_matches]);
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

    public function free_tips(Request $request)
    {
        $base_url = url('/');
        $page = $request->page ?? 1;
        
        $tips = Cache::rememberForever("free_tips", function (){
            $tips = FreeTip::where('status', 1)
                                ->orderBy('match_time', 'DESC')
                                ->get();

            return $tips;
        });

        return response()->json(['status' => true, 'data' => $tips]);
    }
    
    public function another_tips(Request $request)
    {
        $date = $request->date ?? date('Y-m-d');
$timezone = get_option('timezone') ?? 'Africa/Lagos';

// Convert the date to start and end timestamps in the desired timezone
$startOfDay = Carbon::parse($date, $timezone)->startOfDay()->timestamp;
$endOfDay   = Carbon::parse($date, $timezone)->endOfDay()->timestamp;

$tips = AnotherTip::where('status', 1)
    ->whereBetween('match_time', [$startOfDay, $endOfDay]) // <-- use actual column
    ->orderBy('match_time', 'DESC')
    ->get();

    return response()->json([
        'status' => true,
        'date'   => $date,
        'data'   => $tips
    ]);
        // });

        return response()->json(['status' => true, 'data' => $tips, 'date' => $date]);
    }
    
    public function tips(Request $request)
    {
        $base_url = url('/');
        $page = $request->page ?? 1;
        $date = $request->date ?? date('Y-m-d');
    
        // Set your desired timezone
        $timezone = get_option('timezone');
    
        // Get start and end timestamps for the day in your timezone
        $startOfDay = Carbon::createFromFormat('Y-m-d H:i:s', $date . ' 00:00:00', $timezone)->timestamp;
        $endOfDay = Carbon::createFromFormat('Y-m-d H:i:s', $date . ' 23:59:59', $timezone)->timestamp;
    
        // Debug (optional): log the timestamps being queried
        // \Log::info("Querying tips from $startOfDay to $endOfDay for date $date");
    
        $tips = Cache::rememberForever("tips_{$date}", function () use ($startOfDay, $endOfDay) {
            return Tip::where('status', 1)
                      ->whereBetween('match_time', [$startOfDay, $endOfDay])
                      ->orderBy('match_time', 'DESC')
                      ->get();
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
    
    /**
    * Store a newly created resource in storage.
    *
    * @param  \Illuminate\Http\Request  $request
    * @return \Illuminate\Http\Response
    */
    public function uploadLogo(Request $request)
    {
        $validator = \Validator::make($request->all(), [
            'image' => 'required|image',
            'filename' => 'required|string',
        ]);
    
        if ($validator->fails()) {
            return response()->json(['status' => false, 'message' => $validator->errors()->all()]);
        }
    
        $image = null;
    
        if ($request->hasFile('image')) {
            $file = $request->file('image');
            $file_path = public_path('uploads/logo/');
            if (!file_exists($file_path)) {
                mkdir($file_path, 0755, true);
            }
    
            $file_name = $request->input('filename');
            $file->move($file_path, $file_name);
            $image = asset('public/uploads/logo/' . $file_name);
        }
    
        return response()->json(['status' => $image != null, 'image' => $image]);
    }

    
    // News Api
    public function news(Request $request)
    {
        $seconds = 60 * 120;
        $news = Cache::remember("news", $seconds, function () use ($request){
            
            $context = stream_context_create(
    array(
        "http" => array(
            "header" => "User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        )
    )
);

            $url = "https://www.90min.com/posts.rss";

            $xml = file_get_contents($url, false, $context);
            $rss = simplexml_load_string($xml);
    
            $namespaces = $rss->getNamespaces(true);
            $items = [];
            $titles = '';
            $descriptions = '';
    
            foreach ($rss->channel->item as $item) {
                $media_content = $item->children($namespaces['media']);
                $imageAlt = '';
                foreach ($media_content as $i) {
                    $imageAlt = (string)$i->attributes()->url;
                }
    
                $titles = (string)$item->title;
                $links = (string)$item->link;
                $descriptions = (string)$item->description;
                $pubDate = substr((string) $item->pubDate, 0, -15);
    
                if (strpos(strtolower($titles), "covid") !== false || strpos(strtolower($descriptions), "covid") !== false) {
                    //echo "Word Found!";
                } else {
                    $items[] = [
                        'title' => $titles,
                        'link' => $links,
                        'description' => $descriptions,
                        'pubDate' => $pubDate,
                        'image' => $imageAlt ?? '',
                    ];
                }
            }
            foreach ($items as &$item) {
                $item["news_type"] = $item["news_type"] ?? "api";
            }
            // Sort the array based on the "pubDate" field
            usort($items, function ($a, $b) {
                $dateA = strtotime($b['pubDate']);
                $dateB = strtotime($a['pubDate']);
    
                return $dateA - $dateB;
            });
    
            $object = array('news' => $items);
            return json_encode($object);
        });
        
        return $news;

    }
    

    public function news_details(request $request)
    {
        $details = Cache::rememberForever($request->url, function () use ($request){
            return news_details($request->url);
        });
        
        return $details;
    }
    
    public function freefootballtips(request $request){
        ini_set('max_execution_time', 0);
        
        $date = str_replace('today', '', $request->date ?? '');
        $seconds = 60 * 120;
        $items = Cache::remember("freefootballtips_$date", $seconds, function () use ($date){
    
            $baseUrl = 'https://www.footballtipspredictions.com/football-predictions-tips/' . $date;
      
            $dom = new Dom;
        
            $dom->loadFromUrl($baseUrl);
            $body = $dom->find('#gamedetail'); 
        
            $items = [];
            $i = 0;
            foreach ($body->find('section') as $key => $value) {
                
                $fulldate = date('Y-m-d');
                if($date == 'yesterday'){
                    $fulldate = date('Y-m-d',strtotime("-1 days"));
                }else if($date == 'tomorrow'){
                    $fulldate = date('Y-m-d',strtotime("+1 days"));
                }
                
                $headline = $value->find('.ml__headline', 0);
                if($headline != null){
                    // $items[$i]['country_name'] = $headline->find('img', 0)->getAttribute('src', 0) ?? '';
                    // $items[$i]['country_image'] = $headline->find('li a', 0)->innerText ?? '';
                    // $items[$i]['link'] = $headline->find('a', 0)->getAttribute('href') ?? '';
                    
                    $matches = [];
                    foreach ($value->find('.tipsrow') as $key2 => $match) {
            
                        $time = trim($match->find('.tipscell--time')->innerText ?? '');
                        $team_one_name = trim($match->find('.tipscell--grow .tipscell__text', 0)->innerText ?? '');
            
                        $team_one_image = "https://www.footballtipspredictions.com/logosite/teams/" . get_image_name($team_one_name) . ".png";
            
                        $team_two_name = trim($match->find('.tipscell--grow .tipscell__text', 1)->innerText ?? '');
            
                        $team_two_image = "https://www.footballtipspredictions.com/logosite/teams/" . get_image_name($team_two_name) . ".png";
            
                        $tip = trim($match->find('.tipscell--score .tipscell__text', 0)->innerText ?? '');
                        $odds = trim($match->find('.tipscell--score .tipscell__text', 1)->innerText ?? '');
                        $link = trim($match->find('a', 0)->getAttribute('href') ?? '');
            
            
                                    // 
                        $items[] = [
                            'time' => "$fulldate $time",
                            'team_one_name' => $team_one_name,
                            'team_one_image' => $team_one_image,
                            'team_two_name' => $team_two_name,
                            'team_two_image' => $team_two_image,
                            'league_name' => $headline->find('li a', 0)->innerText ?? '',
                            'tip' => $tip,
                            'odds' => $odds,
                            'link' => $link,
                        ];
                    }
                    $i++;
                }
            }
            
            return $items;
        
        });
    
        
        return response()->json(['status' => true, 'data' => $items]);
    }
    
    public function freefootballtips_details(request $request){
        ini_set('max_execution_time', 0);
        
        $link = $request->link;
        
        $details = Cache::rememberForever($link, function () use ($link){
            
            $dom = new Dom;

            $dom->loadFromUrl($link);
            $body = $dom->find('.ml__wrap'); 
        
            $data = [];
            $i = 0;
            
            $data['home'] = $body->find('.detailsgame-odds .detailsgame-odds__item', 0)->find('span', 1)->text ?? '';
            $data['draw'] = $body->find('.detailsgame-odds .detailsgame-odds__item', 1)->find('span', 1)->text ?? '';
            $data['away'] = $body->find('.detailsgame-odds .detailsgame-odds__item', 2)->find('span', 1)->text ?? '';
        
            $data['prediction'] = trim($body->find('.prediction .tipdescri', 0)->text ?? '');
            $data['odds'] = trim($body->find('.prediction .tipdescri', 1)->text ?? '');
            $data['correct_score_prediction'] = trim($body->find('.prediction .tipdescri', 2)->text ?? '');
            $data['stake'] = trim($body->find('.prediction .tipdescri', 3)->text ?? '');
            //
            $form = '';
            foreach ($body->find('.team-form', 0)->find('.formteam') as $key => $value) {
                $form .=  str_replace('_', '-', str_replace(' ' , '', str_replace('formteam', '', $value->getAttribute('class'))));
            }
            $data['form']['home'] = ltrim($form, '-');
        
            $form = '';
            foreach ($body->find('.team-form', 1)->find('.formteam') as $key => $value) {
                $form .=  str_replace('_', '-', str_replace(' ' , '', str_replace('formteam', '', $value->getAttribute('class'))));
            }
            $data['form']['away'] = ltrim($form, '-');
        
            $underOver = ($body->find('.chart-section', 2)->find('figcaption')->innerText ?? '');
            preg_match_all('!\d+!', $underOver, $result);
            $data['under']['home'] = $result[0][0] ?? '';
            $data['over']['home'] = $result[0][1] ?? '';
        
            $underOver = ($body->find('.chart-section', 3)->find('figcaption')->innerText ?? '');
            preg_match_all('!\d+!', $underOver, $result);
            $data['under']['away'] = $result[0][0] ?? '';
            $data['over']['away'] = $result[0][1] ?? '';
        
        
            //
            $last = ($body->find('.chart-section', 0)->find('figcaption')->innerText ?? '');
            preg_match_all('!\d+!', $last, $result);
            $data['last_10_games']['home'] = [
                'win' => $result[0][0] ?? '', 
                'lost' => $result[0][1] ?? '', 
                'draw' => $result[0][2] ?? '',
            ];
        
            //
            $last = ($body->find('.chart-section', 1)->find('figcaption')->innerText ?? '');
            preg_match_all('!\d+!', $last, $result);
            $data['last_10_games']['away'] = [
                'win' => $result[0][0] ?? '', 
                'lost' => $result[0][1] ?? '', 
                'draw' => $result[0][2] ?? '',
            ];
        
            $head2headBody = $body->find('.content-section', 8)->find('table tbody');
            $head2head = [];
            foreach ($head2headBody->find('tr') as $key => $value) {
                $teams = explode(' vs ', $value->find('td', 1)->innerText ?? '');
                $scores = explode(' - ', $value->find('td', 3)->innerText ?? '');
        
                $team_one_image = "https://www.footballtipspredictions.com/logosite/teams/" . get_image_name($teams[0]) . ".png";
                $team_two_image = "https://www.footballtipspredictions.com/logosite/teams/" . get_image_name($teams[1]) . ".png";
        
                $head2head[$key]['time'] = $value->find('td', 0)->innerText ?? '';
                $head2head[$key]['league'] = $value->find('td', 2)->innerText ?? '';
                $head2head[$key]['team_one_name'] = $teams[0];
                $head2head[$key]['team_one_image'] = $team_one_image;
                $head2head[$key]['team_one_goals'] = $scores[0];
                $head2head[$key]['team_two_name'] = $teams[1];
                $head2head[$key]['team_two_image'] = $team_two_image;
                $head2head[$key]['team_two_goals'] = $scores[1];
        
            }
        
            $data['head2head'] = $head2head;
        
            $recentsBody = $body->find('.content-section', 9)->find('table tbody');
            $recents = [];
            foreach ($head2headBody->find('tr') as $key => $value) {
                $teams = explode(' vs ', $value->find('td', 1)->innerText ?? '');
                $scores = explode(' - ', $value->find('td', 3)->innerText ?? '');
        
                $team_one_image = "https://www.footballtipspredictions.com/logosite/teams/" . get_image_name($teams[0]) . ".png";
                $team_two_image = "https://www.footballtipspredictions.com/logosite/teams/" . get_image_name($teams[1]) . ".png";
        
                $recents[$key]['time'] = $value->find('td', 0)->innerText ?? '';
                $recents[$key]['league'] = $value->find('td', 2)->innerText ?? '';
                $recents[$key]['team_one_name'] = $teams[0];
                $recents[$key]['team_one_image'] = $team_one_image;
                $recents[$key]['team_one_goals'] = $scores[0];
                $recents[$key]['team_two_name'] = $teams[1];
                $recents[$key]['team_two_image'] = $team_two_image;
                $recents[$key]['team_two_goals'] = $scores[1];
        
            }
            $data['recents']['home'] = $recents;
        
            $recentsBody = $body->find('.content-section', 10)->find('table tbody');
            $recents = [];
            foreach ($head2headBody->find('tr') as $key => $value) {
                $teams = explode(' vs ', $value->find('td', 1)->innerText ?? '');
                $scores = explode(' - ', $value->find('td', 3)->innerText ?? '');
        
                $team_one_image = "https://www.footballtipspredictions.com/logosite/teams/" . get_image_name($teams[0]) . ".png";
                $team_two_image = "https://www.footballtipspredictions.com/logosite/teams/" . get_image_name($teams[1]) . ".png";
        
                $recents[$key]['time'] = $value->find('td', 0)->innerText ?? '';
                $recents[$key]['league'] = $value->find('td', 2)->innerText ?? '';
                $recents[$key]['team_one_name'] = $teams[0];
                $recents[$key]['team_one_image'] = $team_one_image;
                $recents[$key]['team_one_goals'] = $scores[0];
                $recents[$key]['team_two_name'] = $teams[1];
                $recents[$key]['team_two_image'] = $team_two_image;
                $recents[$key]['team_two_goals'] = $scores[1];
        
            }
            $data['recents']['away'] = $recents;
            return $data;
        });
        
        return response()->json(['status' => true, 'data' => $details]);
    }
    
    public function xgscore(Request $request)
    {
        $base_url = 'https://api.xgscore.io/';
        $url = $base_url . $request->url;
        
        
        $seconds = 4 * 60;
        $data = Cache::remember("$url", $seconds, function () use ($request, $url){
            
            $client = new \GuzzleHttp\Client();
            $response = $client->get($url); 
            $data = json_decode($response->getBody());
            

            return $data;
        });

        return $data;
    }
    
    public function rapidApi(Request $request)
    {
        $path = $request->path;
    
        if (!$path) {
            return response()->json(['error' => 'Missing API path'], 400);
        }
    
        $baseUrl = 'https://api-football-v1.p.rapidapi.com/';
        $fullUrl = $baseUrl . $path;
    
        $seconds = is_numeric($request->cache_time) ? (int) $request->cache_time : 7200;
    
        $cacheKey = "rapid_{$path}";
    
        // Normalize cache key
        $cacheKey = preg_replace('/[^A-Za-z0-9_\-]/', '_', $cacheKey);
    
        $data = Cache::remember($cacheKey, $seconds, function () use ($fullUrl) {
            $client = new \GuzzleHttp\Client();
    
            $response = $client->request('GET', $fullUrl, [
                'headers' => [
                    'x-rapidapi-key' => 'f8d8e1377bmsh6323da85e61df82p1b05e5jsn8b16282c4110',
                    'x-rapidapi-host' => 'api-football-v1.p.rapidapi.com',
                ],
            ]);
    
            return json_decode($response->getBody());
        });
    
        return response()->json($data);
    }

}

if ( ! function_exists('get_image_name')){
    function get_image_name($string = ''){
        $image = str_replace(' ', '-', strtolower($string));
        return $image;
    }
}
