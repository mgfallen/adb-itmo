package handmade_market

import "time"

type ReportRow struct {
	RecordID               int64
	ClientID               int64
	ClientName             string
	ClientAddress          string
	ClientBirthday         time.Time
	ClientEmail            string
	TotalPaidAmount        float64
	MonthlyOrdersCount     int64
	AvgMonthlyOrderPrice   float64
	MedianCompletionDays   float64
	PopularProductCategory *string
	PopularMasterID        *int64
	CountCreated           int64
	CountInProgress        int64
	CountCompleted         int64
	CountUncompleted       int64
	ReportingPeriod        string
}
