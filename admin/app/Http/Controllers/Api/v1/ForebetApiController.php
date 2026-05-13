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

class ForebetApiController extends Controller
{
    
    public function predictions(Request $request)
    {
        ini_set('max_execution_time', 0);
        //@set_time_limit(1000);
        
        $date = $request->date ?? date('Y-m-d');
        $url = "https://www.forebet.com/en/football-predictions/predictions-1x2/$date";
        if($request->type == 'predictions-1x2'){
            $url = "https://www.forebet.com/en/football-predictions/predictions-1x2/$date";
        }elseif($request->type == 'under-over-25-goals'){
            $url = "https://www.forebet.com/en/football-predictions/under-over-25-goals/$date";
        }elseif($request->type == 'double-chance-predictions'){
            $url = "https://www.forebet.com/en/football-predictions/double-chance-predictions/$date";
        }
        
        
        $ch = curl_init(); // initialize curl

curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

// Pretend to be a real browser
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language: en-US,en;q=0.5',
]);

// Optional: follow redirects
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);

// Execute the request
$response = curl_exec($ch);

// Check for errors
if (curl_errno($ch)) {
    return 'Curl error: ' . curl_error($ch);
} else {
    return $response; // page content
}

        
        $seconds = 60 * 60;
        // $matches = Cache::remember("predictions", $seconds, function () use ($url){
            require_once(public_path('php/rex-tools.php'));
            $context = stream_context_create(
                array(
                    "http" => array(
                       "header" => 
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n" .
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n" .
            "Accept-Language: en-US,en;q=0.5\r\n" .
            "Referer: https://www.google.com/"
                    )
                )
            );
        
        	$html = file_get_html($url, false, $context);
           
            $dom = new Dom;
            $dom->loadStr($html);
        
            $matches = [];
            $rows = $dom->find('.rcnt');
        
            foreach ($rows as $row) {
                $homeTeam = $row->find('.tnms .homeTeam')->innerText ?? '';
                $awayTeam = $row->find('.tnms .awayTeam')->innerText ?? '';
                $time = $row->find('time')->innerText ?? '';
                $percentage = $row->find('.fprc', 0);
                
                try {
                    $prediction = $row->find('.predict', 0);
        
                    if($prediction == null){
                        $prediction = $row->find('.predict_y', 0);
                        
                    }
        
                    if($prediction == null){
                        $prediction = $row->find('.predict_no', 0);
                    }
        
                    $league_name = '';
                    $league_image = '';
        
                    $league = $row->find('.shortagDiv', 0);
        
                    if($league != null){
                        $league_name = $league->find('img')->getAttribute('onclick') ?? '';
        
                        preg_match("/'([^']+)'/i", $league_name, $countryMatch);
                        preg_match("/'([^']+)',\s*'([^']+)'/i", $league_name, $leagueMatch);
        
                        $c = isset($countryMatch[1]) ? $countryMatch[1] : null;
                        $l = isset($leagueMatch[2]) ? $leagueMatch[2] : null;
        
                        $league_name = $c . ' ' . $l;
        
                        $league_image = $league->find('img')->getAttribute('src') ?? '';
                    }
        
                    $homePercentage = null;
                    $drawPercentage = null;
                    $awayPercentage = null;
        
                    if($percentage != null){
                        $homePercentage = $percentage->find('span', 0)->text ?? '';
                        $drawPercentage = $percentage->find('span', 1)->text ?? '';
                        $awayPercentage = $percentage->find('span', 2)->text ?? '';
        
                        if($awayPercentage == '' && $drawPercentage != ''){
                            $awayPercentage = $drawPercentage;
                            $drawPercentage = '';
                        }
                    }
        
                    $prediction_status = $prediction != null ? ($prediction->getAttribute('class') ?? '') : '';
                    $matches[] = [
                        'league_name' => $league_name,
                        'league_image' => $league_image,
                        'homeTeam' => $homeTeam,
                        'awayTeam' => $awayTeam,
                        'time' => $time,
                        'percentage' => [
                            'home' => $homePercentage,
                            'draw' => $drawPercentage,
                            'away' => $awayPercentage,
                        ],
                        'prediction' => $prediction != null ? ($prediction->innerText ?? '') : '',
                        'prediction_status' => $prediction_status,
                        'prediction_score' => trim($row->find('.ex_sc', 0)->innerText ?? ''),
                        'avg_goals' => trim($row->find('.avg_sc', 0)->innerText ?? ''),
                        'score' => trim($row->find('.lscr_td .lscrsp', 0)->innerText ?? ''),
                        'status' => trim($row->find('.lmin_td', 0)->innerText ?? ''),
                    ];
                } catch (\Exception $e) {
                    dd($e);
                }
            }
        //     return $matches;
        // });

        return response()->json(['status' => true, 'data' => $matches]);
    }
    
    
    

}
