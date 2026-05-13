<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Payment;
use Yajra\DataTables\Facades\DataTables;

class PaymentController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Request $request)
    {
        $payments = Payment::with(['user', 'subscription'])->orderBy('id', 'DESC');
        
        if ($request->ajax()){
            return DataTables::of($payments)
                ->editColumn('name', function ($payment) {
                    return $payment->user->name;
                })
                ->editColumn('platform', function ($payment) {
                    return strtoupper($payment->platform);
                })
                ->addColumn('action', function($payment) {

                    $action = '<div class="dropdown">
                                    <button class="btn btn-primary btn-sm dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                        ' . _lang('Action') . '
                                    </button>
                                    <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
                    $action .= '<a href="' . route('payments.show', $payment->id) . '" class="dropdown-item ajax-modal" data-title="' . _lang('Details') . '">
                                        <i class="fas fa-eye"></i>
                                        ' . _lang('Details') . '
                                    </a>';
                    $action .= '</div>
                            </div>';
                    return $action;
                })
                ->rawColumns(['action', 'platform'])
                ->make(true);
        }

        return view('backend.payments.index');
    }

    /**
     * Display the specified resource.
     *
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function show(Request $request, $id)
    {
        $payment = Payment::find($id);

        if (!$request->ajax()) {
            return view('backend.payments.modal.show', compact('payment'));
        } else {
            return view('backend.payments.modal.show', compact('payment'));
        }
    }
}

