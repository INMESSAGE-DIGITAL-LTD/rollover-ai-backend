<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use App\Models\Highlight;
use DataTables;
use Validator;

class HighlightController extends Controller
{
    /**
    * Display a listing of the resource.
    *
    * @return \Illuminate\Http\Response
    */
    public function index(Request $request)
    {
        $highlights = Highlight::orderBy('id', 'DESC');

        if ($request->ajax()) {
            return DataTables::of($highlights)
                ->addColumn('team_one', function ($highlight) {
                    if($highlight->team_one_image_type != 'none'){
                        return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . $highlight->team_one_display_image . '"><span class="ml-2">'
                        . $highlight->team_one_name .
                        '</span></div>';
                    }
                    return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . asset('public/default/default-team.png') . '"><span class="ml-2">'
                        . $highlight->team_one_name .
                        '</span></div>';
                })
                ->addColumn('team_two', function ($highlight) {
                    if($highlight->team_two_image_type != 'none'){
                        return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . $highlight->team_two_display_image . '"><span class="ml-2">'
                        . $highlight->team_two_name .
                        '</span></div>';
                    }
                    return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . asset('public/default/default-team.png') . '"><span class="ml-2">'
                        . $highlight->team_two_name .
                        '</span></div>';
                })
                ->editColumn('status', function ($user) {
                    return $user->status == 1 ? status(_lang('Active'), 'success') : status(_lang('In-Active'), 'danger');
                })
                ->addColumn('action', function($highlight){

                    $action = '<div class="dropdown">
                                    <button class="btn btn-primary btn-sm dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                        ' . _lang('Action') . '
                                    </button>
                                    <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
                    
                    $action .= '<a href="' . route('highlights.edit', $highlight->id) . '" class="dropdown-item">
                                        <i class="fas fa-edit"></i>
                                        ' . _lang('Edit') . '
                                    </a>';
                    
                    $action .= '<form action="' . route('highlights.destroy', $highlight->id) . '" method="post" class="ajax-delete">'
                                . csrf_field() 
                                . method_field('DELETE') 
                                . '<button type="button" class="btn-remove dropdown-item">
                                        <i class="fas fa-trash-alt"></i>
                                        ' . _lang('Delete') . '
                                    </button>
                                </form>';
                    $action .= '</div>
                            </div>';
                    return $action;
                })
                ->setRowData([
                    'id' => function($highlight) {
                        return $highlight->id;
                    }
                ])
                ->rawColumns(['action', 'status', 'team_one', 'team_two', 'match_time'])
                ->make(true);
        }

        return view('backend.highlights.index');
    }


    /**
    * Show the form for creating a new resource.
    *
    * @return \Illuminate\Http\Response
    */
    public function create(Request $request)
    {
        if( ! $request->ajax()){
            return view('backend.highlights.create');
        }else{
            return view('backend.highlights.modal.create');
        }
    }

    /**
    * Store a newly created resource in storage.
    *
    * @param  \Illuminate\Http\Request  $request
    * @return \Illuminate\Http\Response
    */
    public function store(Request $request)
    {
        $validator = Validator::make($request->all(), [
            
           'title' => 'required|string|max:191',
           'league' => 'required|string|max:191',
           'url' => 'required|string',
           'team_one_name' => 'required|string|max:191',
            'team_one_image_type' => 'required|string|max:20',
            'team_one_url' => 'nullable|required_if:team_one_image_type,url|url',
            'team_one_image' => 'required_if:team_one_image_type,image|image',
            'team_two_name' => 'required|string|max:191',
            'team_two_image_type' => 'required|string|max:20',
            'team_two_url' => 'nullable|required_if:team_two_image_type,url|url',
            'team_two_image' => 'required_if:team_two_image_type,image|image',
           'status' => 'required|numeric|digits_between:0,11',

        ]);

        if ($validator->fails()) {
            if($request->ajax()){ 
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            }else{
                return back()->withErrors($validator)->withInput();
            }           
        }

        $highlight = new Highlight();
        
        $highlight->title = $request->title;
        $highlight->league = $request->league;
        $highlight->url = $request->url;
        $highlight->team_one_name = $request->team_one_name;
        $highlight->team_one_image_type = $request->team_one_image_type;
        $highlight->team_one_url = $request->team_one_url;
        $highlight->team_two_name = $request->team_two_name;
        $highlight->team_two_image_type = $request->team_two_image_type;
        $highlight->team_two_url = $request->team_two_url;
        $highlight->status = $request->status;

        if ($request->hasFile('team_one_image')) {
            $image = $request->file('team_one_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/highlights/'), $ImageName);
            $highlight->team_one_image = 'public/uploads/images/highlights/' . $ImageName;
        }

        if ($request->hasFile('team_two_image')) {
            $image = $request->file('team_two_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/highlights/'), $ImageName);
            $highlight->team_two_image = 'public/uploads/images/highlights/' . $ImageName;
        }

        $highlight->save();

        cache()->forget('highlights');

        if(! $request->ajax()){
            return back()->with('success', _lang('Information has been added sucessfully.'));
        }else{
            return response()->json(['result' => 'success', 'redirect' => url()->previous(), 'message' => _lang('Information has been added sucessfully.')]);
        }
    }


    /**
    * Display the specified resource.
    *
    * @param  int  $id
    * @return \Illuminate\Http\Response
    */
    public function show(Request $request, $id)
    {
        $highlight = Highlight::find($id);
        if(! $request->ajax()){
            return view('backend.highlights.show', compact('highlight'));
        }else{
            return view('backend.highlights.modal.show', compact('highlight'));
        } 
    }

    /**
    * Show the form for editing the specified resource.
    *
    * @param  int  $id
    * @return \Illuminate\Http\Response
    */
    public function edit(Request $request,$id)
    {
        $highlight = Highlight::find($id);
        if(! $request->ajax()){
            return view('backend.highlights.edit', compact('highlight'));
        }else{
            return view('backend.highlights.modal.edit', compact('highlight'));
        }  
    }

    /**
    * Update the specified resource in storage.
    *
    * @param  \Illuminate\Http\Request  $request
    * @param  int  $id
    * @return \Illuminate\Http\Response
    */
    public function update(Request $request, $id)
    {
        $validator = Validator::make($request->all(), [
            
           'title' => 'required|string|max:191',
           'league' => 'required|string|max:191',
           'url' => 'required|string',
           'team_one_name' => 'required|string|max:191',
            'team_one_image_type' => 'required|string|max:20',
            'team_one_url' => 'nullable|required_if:team_one_image_type,url|url',
            'team_one_image' => 'nullable|image',
            'team_two_name' => 'required|string|max:191',
            'team_two_image_type' => 'required|string|max:20',
            'team_two_url' => 'nullable|required_if:team_two_image_type,url|url',
            'team_two_image' => 'nullable|image',
           'status' => 'required|numeric|digits_between:0,11',

        ]);

        if ($validator->fails()) {
            if($request->ajax()){ 
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            }else{
                return back()->withErrors($validator)->withInput();
            }           
        }

        $highlight = Highlight::find($id);
        
        $highlight->title = $request->title;
        $highlight->league = $request->league;
        $highlight->url = $request->url;
        $highlight->team_one_name = $request->team_one_name;
        $highlight->team_one_image_type = $request->team_one_image_type;
        $highlight->team_one_url = $request->team_one_url;
        $highlight->team_two_name = $request->team_two_name;
        $highlight->team_two_image_type = $request->team_two_image_type;
        $highlight->team_two_url = $request->team_two_url;
        $highlight->status = $request->status;

        if ($request->hasFile('team_one_image')) {
            $image = $request->file('team_one_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/highlights/'), $ImageName);
            $highlight->team_one_image = 'public/uploads/images/highlights/' . $ImageName;
        }

        if ($request->hasFile('team_two_image')) {
            $image = $request->file('team_two_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/highlights/'), $ImageName);
            $highlight->team_two_image = 'public/uploads/images/highlights/' . $ImageName;
        }

        $highlight->save();

        cache()->forget('highlights');

        if(! $request->ajax()){
            return redirect('highlights')->with('success', _lang('Information has been updated sucessfully.'));
        }else{
            return response()->json(['result' => 'success', 'redirect' => url('highlights'), 'message' => _lang('Information has been updated sucessfully.')]);
        }
    }

    /**
    * Remove the specified resource from storage.
    *
    * @param  int  $id
    * @return \Illuminate\Http\Response
    */
    public function destroy(Request $request, $id)
    {
        $highlight = Highlight::find($id);
        $highlight->delete();

        cache()->forget('highlights');
        
        if(! $request->ajax()){
            return redirect('highlights')->with('success', _lang('Information has been deleted sucessfully.'));
        }else{
            return response()->json(['result' => 'success', 'message' => _lang('Information has been deleted sucessfully.')]);
        }
    }
}
