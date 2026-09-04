export {};

declare global {
  interface RazorpayPaymentSuccessResponse {
    razorpay_payment_id: string;
    razorpay_order_id: string;
    razorpay_signature: string;
  }

  interface RazorpayPaymentFailureResponse {
    error?: {
      code?: string;
      description?: string;
      source?: string;
      step?: string;
      reason?: string;
      metadata?: {
        order_id?: string;
        payment_id?: string;
      };
    };
  }

  interface RazorpayOptions {
    key: string;
    amount: number;
    currency: string;
    name: string;
    description?: string;
    image?: string;
    order_id: string;
    handler?: (response: RazorpayPaymentSuccessResponse) => void | Promise<void>;
    modal?: {
      ondismiss?: () => void;
    };
  }

  interface RazorpayInstance {
    open: () => void;
    on: (event: string, handler: (response: RazorpayPaymentFailureResponse) => void) => void;
  }

  interface RazorpayConstructor {
    new (options: RazorpayOptions): RazorpayInstance;
  }

  interface Window {
    Razorpay: RazorpayConstructor;
  }
}
